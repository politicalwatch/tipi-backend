"""Rate limiting (replaces Flask-Limiter) via slowapi.

The limiter is wired into the app in ``tipi_backend.app`` (``app.state.limiter`` +
the ``RateLimitExceeded`` handler). Decorate routes with ``@limiter.limit(...)``;
those routes must declare a ``request: Request`` parameter (slowapi requirement).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
