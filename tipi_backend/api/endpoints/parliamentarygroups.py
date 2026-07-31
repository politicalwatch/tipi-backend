import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api import cache
from tipi_backend.api.business import get_parliamentarygroups, get_parliamentarygroup
from tipi_backend.api.request_models import AuthorsQuery
from tipi_backend.api.serialization import serialize
from tipi_backend.infrastructure.config.settings import get_settings


log = logging.getLogger(__name__)

router = APIRouter(prefix="/parliamentary-groups", tags=["parliamentary-groups"])


@router.get("/")
def list_parliamentarygroups(query: Annotated[AuthorsQuery, Query()]):
    """Returns list of parliamentary groups."""
    # Name-filtered responses are not cached: the keys only tell compact from
    # full, so caching one would serve a subset as the whole list.
    if query.name:
        return serialize(get_parliamentarygroups(query.model_dump()))

    settings = get_settings()
    cache_key = settings.cache_groups_compact if query.compact else settings.cache_groups
    parliamentary_groups = cache.get(cache_key)
    if parliamentary_groups is None:
        parliamentary_groups = serialize(get_parliamentarygroups(query.model_dump()))
        # No expiry: the engine drops this key when it recalculates the groups.
        cache.set(cache_key, parliamentary_groups)
    return parliamentary_groups


@router.get("/{id}")
def get_parliamentarygroup_item(id: str):
    """Returns details of a parliamentary group."""
    try:
        return serialize(get_parliamentarygroup(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No parliamentary group found"})
