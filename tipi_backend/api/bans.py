"""Temporary bans for addresses that keep tripping the intent gate.

The rate limiter already bounds how fast one address can search. It does nothing about
someone who stays under that ceiling and probes patiently: at 200 searches a day, every
one of them refused, the limiter is content. This counts the refusals the intent gate
produces and stops serving an address that keeps producing them.

Three things about the shape, each of which is a decision rather than an implementation
detail:

**What is counted is "not a search", NOT "an attack".** The intent gate's verdict covers
four things — an instruction to the system, a request to generate content, **a question
addressed to the assistant**, and an attempt to change its behaviour — and only the last
is hostile. Someone typing "hola" or "¿quién eres?" while working out what the box does
lands in exactly the same bucket as someone trying to extract the prompt. Nothing here
can tell them apart, so the tiers are set to what a curious newcomer must not exhaust
rather than to what an attacker is allowed, and they measure persistence over days
rather than bursts. This is the single strongest reason the module ships in shadow.

The planned successor is a separate refusal class for the unambiguously hostile case,
banned instantly and briefly on its own escalating table, leaving this counter for the
merely-not-a-search. The two compose in the right direction: an attack that classifier
misses still lands here and still accumulates, so it needs precision rather than recall.
Nothing here has to change to record it — the outcome is derived from the refusal's own
reason, so a new class files itself.

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

# The one refusal reason that counts toward a ban. The name is the gate's own, and it is
# the honest one: this is "the parser said it was not a search", which is a broader class
# than abuse (see the module docstring). Taken from the same reason string the recording
# half files under, so the two halves cannot drift apart on what is being counted.
COUNTED_REASON = "not_a_speech_search"


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
    if _settings.search_ban_mode == OFF or reason != COUNTED_REASON:
        return 0
    client = client_address(request)
    try:
        return _decide(client)
    except Exception:
        log.exception("Could not record a refusal against %s; no ban decided", client)
        return 0


def _decide(client):
    """Increment every window's counter, then apply the longest tier crossed.

    One counter per window rather than one timestamp list per address: a list would grow
    with the abuse it measures, which is the wrong way round. The counters expire on
    their own, so an address that stops probing needs no cleanup.

    The windows are fixed rather than sliding — a counter starts at the first refusal
    and dies one window later. That makes an address at the boundary marginally harder
    to ban than a truly sliding window would, which is the direction to err in.
    """
    tiers = _settings.ban_tiers
    pipe = _client.pipeline()
    for window in tiers:
        key = _key(f"count:{window}", client)
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
    # Longest ban wins: an actor who crosses the weekly tier has also crossed the hourly
    # one, and the hourly answer is not the interesting one.
    ban, window, count, allowed = max(crossed)

    if enforcing():
        _client.setex(_key("until", client), ban, count)
        log.warning("Banned %s for %ss: %s intent-gate refusals in %ss (limit %s)",
                    client, ban, count, window, allowed)
    else:
        log.warning("WOULD ban %s for %ss: %s intent-gate refusals in %ss (limit %s) "
                    "[mode=%s]", client, ban, count, window, allowed,
                    _settings.search_ban_mode)
    return ban


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
