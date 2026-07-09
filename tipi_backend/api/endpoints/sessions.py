import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import search_sessions, get_session
from tipi_backend.api.request_models import SessionsQuery
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/")
def list_sessions(query: Annotated[SessionsQuery, Query()]):
    """Returns a paginated list of parliamentary sittings (most recent first)."""
    total, pages, page, per_page, sessions = search_sessions(query.model_dump())
    return {
        "query_meta": {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
        },
        "sessions": serialize(sessions),
    }


@router.get("/{id}")
def get_session_item(id: str):
    """Returns a sitting's metadata, its initiative-reference roster and speech count."""
    try:
        return serialize(get_session(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No session found"})
