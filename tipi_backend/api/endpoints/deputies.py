import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from tipi_backend.api import cache
from tipi_backend.api.business import get_deputies, get_deputy, get_deputies_birthdays
from tipi_backend.api.request_models import AuthorsQuery
from tipi_backend.api.serialization import serialize
from tipi_backend.settings import Config


log = logging.getLogger(__name__)

router = APIRouter(prefix="/deputies", tags=["deputies"])


@router.get("/")
def list_deputies(query: Annotated[AuthorsQuery, Query()]):
    """Returns list of active deputies."""
    cache_key = Config.CACHE_DEPUTIES_COMPACT if query.compact else Config.CACHE_DEPUTIES
    deputies = cache.get(cache_key)
    if deputies is None:
        deputies = serialize(get_deputies(query.model_dump()))
        cache.set(cache_key, deputies, timeout=60 * 60)
    return deputies


@router.get("/todays-birthdays")
def todays_birthdays():
    """Returns a list of deputies whose birthday is today."""
    return serialize(get_deputies_birthdays())


@router.get("/{id}")
def get_deputy_item(id: str):
    """Returns details of a deputy."""
    try:
        return serialize(get_deputy(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No deputy found"})
