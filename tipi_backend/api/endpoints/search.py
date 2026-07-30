import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from qhld_ai.domain.errors import NotASpeechQuery
from tipi_data import DoesNotExist
from tipi_backend.api.business import semantic_search_speeches, speech_passages
from tipi_backend.api.request_models import SpeechPassagesQuery, SpeechSearchQuery
from tipi_backend.api.serialization import serialize

log = logging.getLogger(__name__)

# Own router (namespace "search") so deployments without the AI stack (Qdrant,
# provider keys) can drop it via EXCLUDE_NAMESPACES, but tagged "speeches" so
# the docs list it with the other speech routes. Must be registered BEFORE the
# speeches router or /speeches/{id} captures "/speeches/search".
router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.get("/search")
def search_speeches_semantic(query: Annotated[SpeechSearchQuery, Query()]):
    """Natural-language semantic search over speeches.

    Returns `per_page` distinct speeches (passages are grouped by speech), each
    as the same compact card as `/speeches/` plus its relevance score and best
    matching passages. Stateless "show more": echo the speech ids already shown
    as repeated `exclude` params to get the next `per_page` fresh speeches.
    `query_meta` carries what the parser understood (semantic_query, resolved
    filters, notes, unresolved entities) and `has_more`.

    A query that names only filters and no topic ("intervenciones de Pedro
    Sánchez") is a browse: `query_meta.browse` is true, `semantic_query` is empty,
    the speeches come newest-first, and each card's passages are the start of the
    speech — nothing matched anything, so nothing should be shown as a match.
    """
    try:
        meta, results = semantic_search_speeches(query.model_dump())
    except NotASpeechQuery:
        # The input wasn't a speech search (a command, a question to the
        # assistant, an injection). A deterministic client error, not a service
        # outage — 422, so the frontend can tell it apart from the 503 below.
        return JSONResponse(
            status_code=422, content={"Error": "Not a speech search"}
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
def speech_passages_for_query(id: str, query: Annotated[SpeechPassagesQuery, Query()]):
    """Every relevance-floored passage of one speech for a natural-language query.

    The results page shows a few matching passages per speech; the detail page
    uses this to highlight ALL of them in the transcript. Two path segments after
    ``/speeches`` so it never shadows (nor is shadowed by) ``/speeches/{id}``.
    """
    try:
        return {"passages": speech_passages(id, query.model_dump())}
    except DoesNotExist:
        return JSONResponse(
            status_code=404, content={"Error": "Speech not found"}
        )
    except NotASpeechQuery:
        return JSONResponse(
            status_code=422, content={"Error": "Not a speech search"}
        )
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=503, content={"Error": "Search is temporarily unavailable"}
        )
