import logging

from fastapi import APIRouter

from tipi_backend.api.business import get_initiative_types
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/initiative-types", tags=["initiative-types"])


@router.get("/")
def list_initiative_types():
    """Returns list of initiative types."""
    return serialize(get_initiative_types())
