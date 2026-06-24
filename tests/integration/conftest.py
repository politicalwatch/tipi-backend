"""Integration-tier fixtures.

These tests need a reachable prod-copy Mongo. When none is configured/reachable (the
common case: a plain ``uv run pytest`` with no ``MONGO_*`` set), they **skip** rather
than fail — so the default run stays green anywhere. The probe uses a short timeout so
that skipping is fast.
"""

import os

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError


@pytest.fixture(scope="session", autouse=True)
def require_live_mongo():
    host = os.environ.get("MONGO_HOST", "localhost")
    port = int(os.environ.get("MONGO_PORT", "27017"))
    probe = MongoClient(
        host=host,
        port=port,
        username=os.environ.get("MONGO_USER"),
        password=os.environ.get("MONGO_PASSWORD"),
        serverSelectionTimeoutMS=800,
    )
    try:
        probe.admin.command("ping")
    except PyMongoError as exc:
        pytest.skip(
            f"integration tests need a reachable Mongo at {host}:{port} "
            f"(set MONGO_* to a prod-copy DB) — {exc}"
        )
    finally:
        probe.close()
