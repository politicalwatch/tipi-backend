"""Unit tests for the consolidated Pydantic ``Settings`` — no infrastructure.

Pin the typed coercion the migration introduces: env vars are always strings, so
these assert booleans and ints are parsed correctly rather than truthy-string
accidents. ``_env_file=None`` keeps these from reading the repo-root ``.env``.
"""

import pytest

from tipi_backend.infrastructure.config.settings import Settings

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("raw", ["False", "false", "0", "no", "off"])
def test_debug_falsey_strings_are_false(raw):
    assert Settings(_env_file=None, debug=raw).debug is False


@pytest.mark.parametrize("raw", ["True", "true", "1", "yes", "on"])
def test_debug_truthy_strings_are_true(raw):
    assert Settings(_env_file=None, debug=raw).debug is True


def test_use_alerts_false_string_is_false():
    assert Settings(_env_file=None, use_alerts="False").use_alerts is False


def test_int_fields_coerced():
    settings = Settings(_env_file=None, port="8080", tagger_max_words="10")
    assert settings.port == 8080
    assert settings.tagger_max_words == 10


def test_defaults():
    # ``_env_file=None`` disables the .env file but NOT os.environ; conftest sets
    # a few vars there (USE_ALERTS, CACHE_REDIS_HOST, MONGO_*), so only assert the
    # fields nothing in the test environment overrides.
    settings = Settings(_env_file=None)
    assert settings.debug is True
    assert settings.ip == "0.0.0.0"
    assert settings.port == 5000
    assert settings.name == "test"
    assert settings.version == "1.0"
    assert settings.exclude_namespaces == ""
    assert settings.country == "spain"
    assert settings.max_content_length == 20 * 1024 * 1024
    assert settings.tagger_max_words == 2500
    assert settings.cache_tags == "tagging-tags"
    assert settings.cache_redis_db == 8
