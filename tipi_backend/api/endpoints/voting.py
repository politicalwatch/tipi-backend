import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tipi_backend.api.business import get_voting
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/voting", tags=["voting"])


@router.get("/{initiative_id}")
def get_voting_item(initiative_id: str):
    """Returns details of a voting."""

    def to_reference(id):
        return id.replace("-", "/")

    try:
        log.info(to_reference(initiative_id))
        return serialize(get_voting(to_reference(initiative_id)))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No votings found"})
