import logging

from fastapi import APIRouter

from tipi_backend.api.business import get_places
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/")
def list_places():
    """Returns list of places."""
    return serialize(get_places())
