import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api import cache
from tipi_backend.api.business import get_parliamentarygroups, get_parliamentarygroup
from tipi_backend.api.request_models import AuthorsQuery
from tipi_backend.api.serialization import serialize
from tipi_backend.settings import Config


log = logging.getLogger(__name__)

router = APIRouter(prefix="/parliamentary-groups", tags=["parliamentary-groups"])


@router.get("/")
def list_parliamentarygroups(query: Annotated[AuthorsQuery, Query()]):
    """Returns list of parliamentary groups."""
    cache_key = Config.CACHE_GROUPS
    parliamentary_groups = cache.get(cache_key)
    if parliamentary_groups is None:
        parliamentary_groups = serialize(get_parliamentarygroups(query.model_dump()))
        cache.set(cache_key, parliamentary_groups, timeout=60 * 60)
    return parliamentary_groups


@router.get("/{id}")
def get_parliamentarygroup_item(id: str):
    """Returns details of a parliamentary group."""
    try:
        return serialize(get_parliamentarygroup(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No parliamentary group found"})
