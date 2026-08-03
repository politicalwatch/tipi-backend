"""Consolidated environment configuration as a single Pydantic ``Settings``.

Replaces the old hand-rolled ``tipi_backend.settings.Config`` (plain ``os.environ``
reads with manual string coercion, ``eval`` and nested dicts). All env config the
backend consumes lives here; access it through the memoised ``get_settings()``.

Only fields actually read by the app are kept — the flask-restx / Flask-Caching
leftovers and the unused ``MONGODB_SETTINGS`` (``tipi_data`` reads ``MONGO_*``
itself) were dropped in the migration.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # Server
    debug: bool = True  # was FLASK_DEBUG; Flask is gone — only feeds uvicorn reload=
    ip: str = "0.0.0.0"
    port: int = 5000

    # App metadata (OpenAPI docs) — previously read raw from env in app.py
    name: str = "test"
    description: str = (
        "This document includes all the methods that the {} API offers its users."
    )
    version: str = "1.0"
    # Substring-matched against namespace names in app.py; kept as a str for parity.
    exclude_namespaces: str = ""

    # Behavior
    use_alerts: bool = False
    country: str = "spain"
    max_content_length: int = 20 * 1024 * 1024  # 20 MiB (was eval()'d from env)
    tagger_max_words: int = 2500

    # Shared secret the Nuxt server sends when forwarding a search rating. There are
    # no user accounts yet, so this is what distinguishes "came through our frontend"
    # from "was curled at the endpoint". Empty means reject every rating: a
    # misconfigured deploy should fail closed, not accept anonymous writes.
    search_rating_token: str = ""

    # Cache keys. One per response variant: a single key per endpoint would serve
    # the compact list as the full one, whichever request populated it first.
    cache_tags: str = "tagging-tags"
    cache_groups: str = "parliamentary-groups"
    cache_groups_compact: str = "parliamentary-groups-compact"
    cache_deputies: str = "deputies"
    cache_deputies_compact: str = "deputies-compact"

    # Redis (flattened from the old CACHE dict — only the keys cache.py reads)
    cache_redis_host: str = "redis"
    cache_redis_port: int = 6379
    cache_redis_password: str = ""
    cache_redis_db: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
