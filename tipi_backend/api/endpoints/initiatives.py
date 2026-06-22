import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tipi_data.models.searches_tracker import SearchesTracker

from tipi_backend.api.business import (
    search_initiatives,
    get_initiative,
    get_initiatives_sitemap,
)
from tipi_backend.api.request_models import InitiativesQuery, InitiativeQuery
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/initiatives", tags=["initiatives"])


class SitemapItem(BaseModel):
    id: str
    updated: datetime | None = None


@router.get("/")
def list_initiatives(query: Annotated[InitiativesQuery, Query()], request: Request):
    """Returns list of initiatives."""
    args = query.model_dump()
    SearchesTracker.save_search(
        args, {"HTTP_USER_AGENT": request.headers.get("user-agent", "")}
    )
    # 'args' is adapted for searching (mutated) inside search_initiatives, after save.
    total, pages, page, per_page, initiatives = search_initiatives(args)
    return {
        "query_meta": {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
        },
        "initiatives": serialize(initiatives),
    }


@router.get("/sitemap", response_model=list[SitemapItem])
def initiatives_sitemap():
    """Returns a lightweight [{id, updated}] list for building the frontend sitemap."""
    return get_initiatives_sitemap()


@router.get("/{id}")
def get_initiative_item(id: str, query: Annotated[InitiativeQuery, Query()]):
    """Returns details of an initiative."""
    try:
        return serialize(get_initiative(id=id, params=query.model_dump()))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No initiative found"})
