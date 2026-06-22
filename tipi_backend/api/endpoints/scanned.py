import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from tipi_backend.api.business import save_scanned, get_scanned, search_verified_scanned
from tipi_backend.api.ratelimit import limiter
from tipi_backend.api.request_models import ScannedBody
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/scanned", tags=["scanned"])


@router.post("/", status_code=201, include_in_schema=False)
@limiter.limit("10/hour")
def create_scanned(request: Request, body: ScannedBody):
    """Create a new scanned."""
    try:
        return save_scanned(body.model_dump())
    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500)


@router.get("/search/{query}", include_in_schema=False)
def search_scanned(query: str):
    """Returns list of verified scanned documents."""
    return serialize(search_verified_scanned(query))


@router.get("/{id}", include_in_schema=False)
def get_scanned_item(id: str):
    """Returns details of a scanned document."""
    try:
        return serialize(get_scanned(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No scanned document found"})
