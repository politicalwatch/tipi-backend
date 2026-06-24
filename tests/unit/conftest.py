"""Tier-1 (no-infra) fixtures."""

import pytest

from tipi_backend.api.ratelimit import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    """slowapi's limiter uses process-wide in-memory storage; reset it around every
    test so rate-limit counts never bleed between tests."""
    limiter.reset()
    yield
    limiter.reset()
