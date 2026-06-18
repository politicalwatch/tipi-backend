import pytest

from tipi_backend.app import create_app
from tipi_backend.settings import Config

# Configure before the app is built.
Config.USE_ALERTS = True


@pytest.fixture(scope="session")
def app():
    """Build the Flask app exactly once for the whole test session.

    Flask-RESTX registers routes on a module-level ``Api`` singleton;
    calling ``create_app()`` more than once in a session triggers a Flask 3
    ``add_url_rule can no longer be called`` error.  The session scope
    prevents that.
    """
    return create_app(config=Config)


@pytest.fixture(scope="session")
def client(app):
    """A session-scoped test client shared across all test files."""
    return app.test_client()
