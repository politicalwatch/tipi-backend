import logging

from fastapi import APIRouter

from tipi_backend.api.business import get_initiative_status


log = logging.getLogger(__name__)

router = APIRouter(prefix="/initiative-status", tags=["initiative-status"])


@router.get("/")
def list_initiative_status():
    """Returns list of initiative status."""
    return get_initiative_status()
