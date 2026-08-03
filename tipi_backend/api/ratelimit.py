"""Rate limiting (replaces Flask-Limiter) via slowapi.

The limiter is wired into the app in ``tipi_backend.app`` (``app.state.limiter`` +
the ``RateLimitExceeded`` handler). Decorate routes with ``@limiter.limit(...)``;
those routes must declare a ``request: Request`` parameter (slowapi requirement).
"""

import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

log = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """slowapi's 429, plus a ``Retry-After`` telling the caller how long to wait.

    Our limits stack three windows (a minute, an hour, a day), and the difference is
    what a client actually needs: a minute's wait and a day's wait deserve different
    words. slowapi records the limit that failed — ``__evaluate_limits`` sets
    ``request.state.view_rate_limit`` to ``(failed_limit, args)`` immediately before
    raising — so the reset time of *that* window is what we report.

    Not ``Limiter(headers_enabled=True)``, which would look like the obvious way to get
    this header: slowapi's ``_inject_headers`` RAISES when a limited handler returns a
    plain dict rather than a ``Response``, and that is every limited route we have. It
    would mean adding a ``response: Response`` parameter to all of them and decorating
    every successful response with ``X-RateLimit-*`` headers nobody asked for.

    Note the header is useless to a browser on another origin unless CORS exposes it —
    see ``expose_headers`` where the middleware is configured in ``tipi_backend.app``.
    """
    response = _rate_limit_exceeded_handler(request, exc)
    try:
        limit, args = request.state.view_rate_limit
        reset_at, _ = limiter.limiter.get_window_stats(limit, *args)
        # Floored at 1: a request landing on the window boundary would otherwise be told
        # to retry after zero seconds, which reads as "retry immediately" and won't work.
        response.headers["Retry-After"] = str(max(1, int(reset_at - time.time())))
    except Exception:
        # A missing header is a worse message, not a broken endpoint — never let this
        # turn a 429 into a 500.
        log.warning("Could not compute Retry-After for a rate-limited request",
                    exc_info=True)
    return response
