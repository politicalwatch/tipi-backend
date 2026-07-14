import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import search_speeches, get_speech
from tipi_backend.api.request_models import SpeechesQuery
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.get("/")
def list_speeches(query: Annotated[SpeechesQuery, Query()]):
    """Returns a paginated list of speeches (compact, without text).

    Filter by ``session`` (a sitting id — returned in delivery order), ``reference``
    (an initiative — the debate view is ``session`` + ``reference``), ``speaker``,
    ``group``, ``legislature``, ``mention`` (a person id named in the speech) and a
    ``startdate``/``enddate`` range."""
    total, pages, page, per_page, speeches = search_speeches(query.model_dump())
    return {
        "query_meta": {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
        },
        "speeches": serialize(speeches),
    }


@router.get("/{id}")
def get_speech_item(id: str):
    """Returns a speech in full, including its per-language text blocks and mentions.

    ``id`` accepts the Congress intervention id (``video_id``, all digits) or the
    internal speech id."""
    try:
        return serialize(get_speech(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No speech found"})
