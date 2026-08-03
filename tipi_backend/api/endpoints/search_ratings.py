"""Search ratings submitted by users of the speech search.

There are no user accounts yet, so a rating is anonymous and the only property we can
actually enforce is that it *arrived through our own frontend*: the Nuxt server holds a
shared secret and sends it as a header, which is what stops anyone from posting ratings
straight at the endpoint. The route stays in the docs on purpose — the token, not
obscurity, is the control.
"""

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from tipi_backend.api.business import save_search_rating
from tipi_backend.api.ratelimit import limiter
from tipi_backend.api.request_models import SearchRatingBody
from tipi_backend.infrastructure.config.settings import get_settings


log = logging.getLogger(__name__)

router = APIRouter(prefix="/search-ratings", tags=["speeches"])


def verify_token(x_qhld_token: Annotated[str | None, Header()] = None):
    """Reject anything that did not come through our frontend.

    A dependency rather than a check inside the handler, for two reasons that both
    matter: dependencies resolve *before* the route body, so the handler's blanket
    ``except Exception -> 500`` cannot swallow this 401; and ``get_settings()`` is read
    here, per request, so a test can set the env var even though the app is built once
    per session.

    The header is declared optional so that a MISSING one is a 401 like a wrong one --
    a required ``Header()`` would raise ``RequestValidationError``, which the app's
    handler turns into a 400.
    """
    expected = get_settings().search_rating_token
    # No configured token means there is no way to tell our frontend from anyone else,
    # so refuse everything rather than accept everything.
    if not expected:
        log.warning("Rating rejected: SEARCH_RATING_TOKEN is not configured")
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    if not x_qhld_token or not secrets.compare_digest(x_qhld_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing token")


@router.post("", status_code=201, dependencies=[Depends(verify_token)])
# Deliberately generous. Every rating reaches us through the Nuxt server, so slowapi --
# which keys on the peer address -- sees a single IP for the entire audience. This is a
# blast-radius cap on the collection, NOT a per-user limit; that one lives in the nitro
# route, which is the only layer that can still see the real client.
@limiter.limit("600/hour")
def create_search_rating(request: Request, body: SearchRatingBody):
    """Record one rating of one speech search."""
    try:
        save_search_rating(body.model_dump())
    except Exception as e:
        log.error(e)
        raise HTTPException(status_code=500)
    return {"status": "ok"}
