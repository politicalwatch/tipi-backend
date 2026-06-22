import logging

from fastapi import APIRouter, HTTPException, Request

from tipi_backend.api.business import save_alert
from tipi_backend.api.ratelimit import limiter
from tipi_backend.api.request_models import AlertBody


log = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", include_in_schema=False)
@limiter.limit("10/hour")
def create_alert(request: Request, body: AlertBody):
    """Create a new alert."""
    try:
        save_alert(body.model_dump())
        # NOTE: preserves the legacy response exactly (HTTP 200 with body `201`);
        # the original flask-restx handler did `return 201`.
        return 201
    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500)
