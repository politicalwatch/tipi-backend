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
