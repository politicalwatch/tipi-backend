import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api.business import (
    get_footprint_by_topic,
    get_footprint_range_by_all_topics,
    get_footprint_by_deputy,
    get_footprint_by_parliamentarygroup,
)
from tipi_backend.api.request_models import (
    FootprintByTopicQuery,
    FootprintByDeputyQuery,
    FootprintByParliamentaryGroupQuery,
)
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/footprint", tags=["footprint"])


@router.get("/by-topic")
def footprint_by_topic(query: Annotated[FootprintByTopicQuery, Query()]):
    """Returns footprint by a specific topic."""
    try:
        return serialize(get_footprint_by_topic(query.model_dump()))
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=404,
            content={"Error": f"No footprint by topic {query.topic} found."},
        )


@router.get("/range-by-all-topics")
def footprint_range_by_all_topics():
    """Returns max deputy and parliamentarygroup's footprint by all topics."""
    try:
        return get_footprint_range_by_all_topics()
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No footprints found."})


@router.get("/by-deputy")
def footprint_by_deputy(query: Annotated[FootprintByDeputyQuery, Query()]):
    """Returns footprint by a specific deputy."""
    try:
        return serialize(get_footprint_by_deputy(query.model_dump()))
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=404,
            content={"Error": f"No footprint by deputy {query.deputy} found."},
        )


@router.get("/by-parliamentarygroup")
def footprint_by_parliamentarygroup(query: Annotated[FootprintByParliamentaryGroupQuery, Query()]):
    """Returns footprint by a specific parliamentary group."""
    try:
        return serialize(get_footprint_by_parliamentarygroup(query.model_dump()))
    except Exception as e:
        log.error(e)
        return JSONResponse(
            status_code=404,
            content={
                "Error": f"No footprint by parliamentary group {query.parliamentarygroup} found."
            },
        )
