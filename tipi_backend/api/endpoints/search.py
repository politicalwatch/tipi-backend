import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import semantic_search_speeches
from tipi_backend.api.request_models import SpeechSearchQuery
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
    """
    try:
        meta, results = semantic_search_speeches(query.model_dump())
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
