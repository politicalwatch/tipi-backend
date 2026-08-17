"""Natural-language speech search.

Both routes here cost real money per call — an LLM parse, an embedding and a rerank —
and both are reached straight from the browser (the frontend calls the public API
directly; only the ratings POST goes through the Nuxt server). That makes the peer
address a real client, so per-IP limits mean something here in a way they do not for
``/search-ratings``.

The caps are sized for a *human* reading results, not for a script: a page of cards
takes tens of seconds to read, so nobody sustains more than a few searches a minute,
and the per-minute cap is therefore not what separates a person from a bot — a bot
paces itself. The hour and day buckets do that work. Registered accounts are the
planned release valve for the shared-address cases these numbers do squeeze (a
newsroom or a campus behind one NAT); until then free anonymous use stays tight.

Caveat before trusting any of it: the container runs uvicorn with
``--forwarded-allow-ips '*'``, which makes it read the LEFTMOST ``X-Forwarded-For``
entry — a value the caller controls. A client rotating that header resets its own
bucket. Narrowing that flag to the real proxy address is what makes the per-IP caps
enforceable; until then ``_SPEND_CEILING`` is the only limit that actually holds.

The caps bound how FAST one address searches, and nothing else. An address staying
under them while spending every request on the intent gate is what ``api.bans``
answers; it refuses to act while the flag above is still ``*``, for the same reason
this caveat exists.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from qhld_ai.domain.errors import SearchRefused
from tipi_data import DoesNotExist
from tipi_backend.api import bans
from tipi_backend.api.business import semantic_search_speeches, speech_passages
from tipi_backend.api.ratelimit import limiter
from tipi_backend.api.request_models import SpeechPassagesQuery, SpeechSearchQuery
from tipi_backend.api.serialization import serialize

log = logging.getLogger(__name__)

# Own router (namespace "search") so deployments without the AI stack (Qdrant,
# provider keys) can drop it via EXCLUDE_NAMESPACES, but tagged "speeches" so
# the docs list it with the other speech routes. Must be registered BEFORE the
# speeches router or /speeches/{id} captures "/speeches/search".
router = APIRouter(prefix="/speeches", tags=["speeches"])

# ONE bucket for both routes and every caller: a spend circuit-breaker, not a usage
# limit. Per-IP caps do nothing against a distributed scraper, nor against the
# spoofable header above, and this is what bounds the provider bill in those cases.
# Set well above plausible real traffic (~33x one address's hourly cap). It is the
# number to RAISE as the audience grows, since exhausting it stops search for
# everyone — which is the trade we accepted for having a ceiling at all.
_SPEND_CEILING = "2000/hour"

# Per address. 10/minute absorbs a human's burst of reformulations; 60/hour is already
# several times the heaviest research pace we can imagine; 200/day is what bounds a
# scraper patient enough to stay under both of the others. slowapi charges BEFORE the
# handler runs, so the 422 and 503 paths below spend quota too — probing the endpoint
# with junk costs the caller, which is what we want.
_SEARCH_LIMITS = "10/minute;60/hour;200/day"
# Roughly 2.5x search: one query legitimately fans out to several detail pages, and
# the frontend caches per (speech, query) for the session, so revisits are free.
_PASSAGE_LIMITS = "30/minute;150/hour;500/day"

# Refusal reasons the client is allowed to see. Anything else is reported as the
# intent gate's, which is true — a hostile query is not a speech search — and is
# the same wording the user would have got before the hostile class existed.
#
# Deliberate: `prompt_injection` is the one reason that can get an address banned
# on a single request, so echoing it back would tell an attacker exactly which
# phrasings trip the classifier and which slip past it. That is free feedback for
# evading it, paid for with nothing, and the honest user loses nothing by the
# masking because both refusals need the same words anyway.
_CLIENT_REASONS = frozenset({"not_a_speech_search", "unsupported_language"})


def _client_reason(refusal):
    return refusal.reason if refusal.reason in _CLIENT_REASONS else "not_a_speech_search"


@router.get("/search")
@limiter.shared_limit(_SPEND_CEILING, scope="speech-search", key_func=lambda: "all")
@limiter.limit(_SEARCH_LIMITS)
def search_speeches_semantic(
    request: Request, query: Annotated[SpeechSearchQuery, Query()]
):
    """Natural-language semantic search over speeches.

    Returns `per_page` distinct speeches (passages are grouped by speech), each
    as the same compact card as `/speeches/` plus its relevance score and best
    matching passages. Stateless "show more": echo the speech ids already shown
    as repeated `exclude` params to get the next `per_page` fresh speeches.
    `query_meta` carries what the parser understood (semantic_query, resolved
    filters, notes, unresolved entities) and `has_more`. `query_meta.labels` maps
    the filter values that mean nothing on their own — the person ids a `mentions`
    filter holds — to the name to show for them. An unresolved entity's `reason` is
    null when nobody answers to that value, and `"filtered_out"` when it WAS
    recognised and the rest of the query rules it out ("Montero de Sumar").

    A query that names only filters and no topic ("intervenciones de Pedro
    Sánchez") is a browse: `query_meta.browse` is true, `semantic_query` is empty,
    the speeches come newest-first, and each card's passages are the start of the
    speech — nothing matched anything, so nothing should be shown as a match.
    """
    rejected = bans.reject_if_banned(request)
    if rejected is not None:
        return rejected
    try:
        meta, results = semantic_search_speeches(query.model_dump())
    except SearchRefused as refusal:
        # The search was refused before retrieval — either the input wasn't a
        # speech search (a command, a question to the assistant, an injection) or
        # it was written in a language we don't serve. A deterministic client
        # error, not a service outage: 422, so the frontend can tell it apart from
        # the 503 below, and `reason` so it can say WHICH — the two need different
        # words, since a refused-for-language user did nothing wrong.
        #
        # Counted here rather than in `business`, so the caller's address stays in
        # this layer: the collection that records WHAT was asked never learns who
        # asked. Only this route counts — `/passages` re-resolves the same query for
        # the detail page and would charge one caller twice for one search.
        bans.record_refusal(request, refusal.reason)
        return JSONResponse(
            status_code=422,
            content={"Error": "Search refused", "reason": _client_reason(refusal)},
        )
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=503, content={"Error": "Search is temporarily unavailable"}
        )
    return {
        "query_meta": meta,
        "results": [
            {
                "speech": serialize(result["speech"]),
                "score": result["score"],
                "highlights": result["highlights"],
            }
            for result in results
        ],
    }


@router.get("/{id}/passages")
@limiter.shared_limit(_SPEND_CEILING, scope="speech-search", key_func=lambda: "all")
@limiter.limit(_PASSAGE_LIMITS)
def speech_passages_for_query(
    request: Request, id: str, query: Annotated[SpeechPassagesQuery, Query()]
):
    """Every relevance-floored passage of one speech for a natural-language query.

    The results page shows a few matching passages per speech; the detail page
    uses this to highlight ALL of them in the transcript. Two path segments after
    ``/speeches`` so it never shadows (nor is shadowed by) ``/speeches/{id}``.
    """
    rejected = bans.reject_if_banned(request)
    if rejected is not None:
        return rejected
    try:
        return {"passages": speech_passages(id, query.model_dump())}
    except DoesNotExist:
        return JSONResponse(
            status_code=404, content={"Error": "Speech not found"}
        )
    except SearchRefused as refusal:
        return JSONResponse(
            status_code=422,
            content={"Error": "Search refused", "reason": _client_reason(refusal)},
        )
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=503, content={"Error": "Search is temporarily unavailable"}
        )
