"""Thin Redis cache helpers (replaces Flask-Caching).

Preserves the previous behavior: pickled Python objects stored in Redis DB 8
(per the ``cache_redis_*`` settings), same keys and TTLs as before. The client is
lazy, so importing this module does not require Redis to be reachable.

``redis.asyncio`` offers a drop-in async client for the Phase 3 async work.
"""

import pickle

import redis

from tipi_backend.infrastructure.config.settings import get_settings

_settings = get_settings()
_client = redis.Redis(
    host=_settings.cache_redis_host,
    port=_settings.cache_redis_port,
    password=_settings.cache_redis_password or None,
    db=_settings.cache_redis_db,
)


def get(key):
    raw = _client.get(key)
    return None if raw is None else pickle.loads(raw)


def set(key, value, timeout=None):
    _client.set(key, pickle.dumps(value), ex=timeout)
