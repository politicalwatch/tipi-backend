import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import get_topics, get_topic
from tipi_backend.api.request_models import KbQuery
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/")
def list_topics(query: Annotated[KbQuery, Query()]):
    """Returns list of topics."""
    if query.knowledgebase is not None:
        return serialize(get_topics(query.knowledgebase.split(",")))
    return serialize(get_topics())


@router.get("/{id}")
def get_topic_item(id: str):
    """Returns details of a topic."""
    try:
        return serialize(get_topic(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No topic found"})
