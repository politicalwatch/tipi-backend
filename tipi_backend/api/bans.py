"""Temporary bans for addresses that keep tripping the intent gate.

The rate limiter already bounds how fast one address can search. It does nothing about
someone who stays under that ceiling and probes patiently: at 200 searches a day, every
one of them refused, the limiter is content. This counts the refusals the intent gate
produces and stops serving an address that keeps producing them.

Three things about the shape, each of which is a decision rather than an implementation
detail:

**Two populations, two tables.** ``not_a_speech_search`` means the parser judged the
input not to be a search, which catches someone typing "hola" or "¿quién eres?" while
working out what the box does as readily as anyone abusing us. Its tiers are therefore
set to what a curious newcomer must not exhaust, and they measure persistence over days
rather than bursts. ``prompt_injection`` is the unambiguously hostile subset — an
attempt to override instructions, extract the prompt, bypass a filter or adopt an
unrestricted persona — and one occurrence is enough to act on.

Counters are keyed per reason so the two never pool: fifteen confused non-searches must
not combine with one hostile query into a ban neither of them earned.

**The classes compose, which is what makes the hostile table safe.** An attack the
classifier does not recognise still fails the intent gate, still gets refused, and still
accumulates on the soft counter. So the hostile class is tuned for precision and its
recall gaps cost little — measured 2026-08-17 at 0 false positives over 35 legitimate
and 10 non-search probes, with 19 of 20 attacks recognised and the twentieth refused as
a plain non-search.

``refused_unsupported_language`` is excluded for a related but weaker reason: it is
someone asking a real question in a language we do not serve, they did nothing wrong,
and the language verdict has its own uncertainty.

**Shadow by default.** The thresholds are reasoned, not measured, and a refusal fails
closed: a wrongly banned user cannot tell it from the site being broken. In shadow the
verdict is computed and logged and the request is served anyway, which turns the
threshold into something the logs can settle.

**Addresses stay here.** The sibling collection ``search_diagnostics`` records what was
asked; this module records who asked too often. Neither holds both, which is what keeps
the privacy decision taken for that collection from quietly widening into one about
identifying requesters.

Every failure path serves the request. A ban store that is down, misconfigured or
unreachable must never turn a search into an error, and must never ban anyone by
accident.
"""

import logging

import redis
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address

from tipi_backend.infrastructure.config.settings import get_settings

log = logging.getLogger(__name__)

_settings = get_settings()

# Lazy, like api.cache: importing this module must not require Redis to be reachable.
_client = redis.Redis(
    host=_settings.cache_redis_host,
    port=_settings.cache_redis_port,
    password=_settings.cache_redis_password or None,
    db=_settings.ban_redis_db,
)

OFF = "off"
SHADOW = "shadow"
ENFORCE = "enforce"

def _key(prefix, client):
    return f"ban:{prefix}:{client}"


def enforcing():
    """Whether a decided ban may actually be acted on.

    The interlock: with ``FORWARDED_ALLOW_IPS`` at ``*`` uvicorn takes the leftmost
    ``X-Forwarded-For`` entry, which is a value the caller writes. Banning on it would
    miss any attacker who rotates the header and would land on whichever third party
    they name instead — worse than not banning at all. So the mode alone cannot switch
    enforcement on; the deployment has to be one where the address means something.
    """
    if _settings.search_ban_mode != ENFORCE:
        return False
    if _settings.forwarded_allow_ips.strip() in ("*", ""):
        log.warning(
            "SEARCH_BAN_MODE is 'enforce' but FORWARDED_ALLOW_IPS is %r, which makes the "
            "client address caller-controlled. Refusing to enforce bans; set it to the "
            "address of the proxy that fronts this deployment.",
            _settings.forwarded_allow_ips)
        return False
    return True


def client_address(request):
    """Who the ban is about.

    ``get_remote_address`` is slowapi's own, deliberately: the ban and the rate limiter
    must never disagree about who the client is, and sharing the function is what
    guarantees it rather than hoping two implementations stay aligned.
    """
    return get_remote_address(request)


def banned_for(request):
    """Seconds remaining on this address's ban, or 0. Never raises."""
    if _settings.search_ban_mode == OFF:
        return 0
    try:
        ttl = _client.ttl(_key("until", client_address(request)))
    except Exception:
        log.exception("Could not read the ban store; serving the request")
        return 0
    # redis-py returns -2 for a missing key and -1 for one with no expiry.
    return ttl if ttl and ttl > 0 else 0


def record_refusal(request, reason):
    """Count one refusal and ban the address if it has crossed a tier. Never raises.

    Returns the ban duration decided, or 0. The return value is what shadow mode
    reports; in enforce mode the ban is already in place by then.
    """
    tiers = _settings.ban_tiers.get(reason)
    if _settings.search_ban_mode == OFF or not tiers:
        return 0
    client = client_address(request)
    try:
        return _decide(client, reason, tiers)
    except Exception:
        log.exception("Could not record a refusal against %s; no ban decided", client)
        return 0


def _decide(client, reason, tiers):
    """Increment every window's counter, then apply the longest tier crossed.

    One counter per window rather than one timestamp list per address: a list would grow
    with the abuse it measures, which is the wrong way round. The counters expire on
    their own, so an address that stops probing needs no cleanup.

    The windows are fixed rather than sliding — a counter starts at the first refusal
    and dies one window later. That makes an address at the boundary marginally harder
    to ban than a truly sliding window would, which is the direction to err in.

    Counters are keyed per REASON, so the two populations never pool: fifteen confused
    non-searches must not combine with one hostile query into a ban neither earned.
    """
    pipe = _client.pipeline()
    for window in tiers:
        key = _key(f"count:{reason}:{window}", client)
        pipe.incr(key)
        # Only the first refusal in a window sets the expiry; NX keeps a later one from
        # pushing the window forward, which would let a steady prober outrun it forever.
        pipe.expire(key, window, nx=True)
    results = pipe.execute()
    counts = {window: results[i * 2] for i, window in enumerate(tiers)}

    crossed = [(ban, window, counts[window], allowed)
               for window, (allowed, ban) in tiers.items()
               if counts[window] >= allowed]
    if not crossed:
        return 0
    # Longest ban wins: an actor who crosses the weekly tier has also crossed the daily
    # one, and the daily answer is not the interesting one.
    ban, window, count, allowed = max(crossed)

    if enforcing():
        _apply(client, ban, count)
        log.warning("Banned %s for %ss: %s %s refusals in %ss (limit %s)",
                    client, ban, count, reason, window, allowed)
    else:
        log.warning("WOULD ban %s for %ss: %s %s refusals in %ss (limit %s) [mode=%s]",
                    client, ban, count, reason, window, allowed,
                    _settings.search_ban_mode)
    return ban


def _apply(client, ban, count):
    """Store the ban, never shortening one already in force.

    Both reasons write the same key, so a plain ``setex`` would let an actor serving a
    thirty-day hostile ban clear it by tripping the soft gate once — the cheaper offence
    overwriting the dearer one. Taking the longer of the two is the whole rule.
    """
    key = _key("until", client)
    remaining = _client.ttl(key)
    if remaining and remaining > ban:
        return
    _client.setex(key, ban, count)


def ban_response(seconds):
    """The 429 a banned caller gets.

    Same status and ``Retry-After`` as the rate limiter's, on purpose: the frontend
    already words a 429, CORS already exposes the header (``app.py``), and a banned
    caller does not need to be told they were singled out.
    """
    return JSONResponse(
        status_code=429,
        content={"Error": "Too many refused searches from this address"},
        headers={"Retry-After": str(max(1, seconds))},
    )


def reject_if_banned(request: Request):
    """Route dependency: 429 a banned address before any paid work happens.

    Returns a response instead of raising so the route can hand it straight back — the
    endpoints here already return ``JSONResponse`` for their error cases rather than
    raising ``HTTPException``.
    """
    remaining = banned_for(request)
    return ban_response(remaining) if remaining and enforcing() else None
