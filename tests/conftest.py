"""Shared pytest fixtures.

Tier-1 (``tests/unit``) runs with **no infrastructure** — no Mongo, no Redis, no
celery broker. The env defaults below are set *before* importing the app so nothing
ever needs to be exported by hand; Tier-1 never actually connects (Mongo and the
cache are mocked per-test, the slowapi limiter is in-memory, and the celery app is
configured for ``memory://`` so ``tipi_tasks.init()`` builds without a broker).

Tier-2 (``tests/integration``, ``-m integration``) needs a reachable prod-copy Mongo;
point it there by exporting ``MONGO_*`` (these ``setdefault`` calls won't override a
real value already in the environment).
"""

import logging
import os

# The app's logging.conf sets the root logger to DEBUG; pymongo's background monitor
# threads then spew DEBUG heartbeats and, at interpreter shutdown, try to log to an
# already-closed stdout ("I/O operation on closed file"). Quiet pymongo for tests — its
# own WARNING level gates record creation even after the app reconfigures the root logger.
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Must run before tipi_backend / tipi_data are imported (settings + clients read env
# at import time).
os.environ.setdefault("MONGO_SKIP_INDEX_INIT", "1")
os.environ.setdefault("MONGO_HOST", "localhost")
os.environ.setdefault("MONGO_PORT", "27017")
os.environ.setdefault("MONGO_USER", "qhld")
os.environ.setdefault("MONGO_PASSWORD", "qhld")
os.environ.setdefault("MONGO_DB_NAME", "qhlddb")
os.environ.setdefault("CACHE_REDIS_HOST", "localhost")
os.environ.setdefault("BROKER", "memory://")
os.environ.setdefault("RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("USE_ALERTS", "True")

import pytest
from fastapi.testclient import TestClient

from tipi_backend.app import create_app
from tipi_backend.settings import Config

# Configure before the app is built.
Config.USE_ALERTS = True


@pytest.fixture(scope="session")
def app():
    """Build the FastAPI app once for the whole test session."""
    return create_app(config=Config)


@pytest.fixture(scope="session")
def client(app):
    """A session-scoped FastAPI TestClient shared across all test files."""
    return TestClient(app)
