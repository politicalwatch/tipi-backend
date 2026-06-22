"""Thin Redis cache helpers (replaces Flask-Caching).

Preserves the previous behavior: pickled Python objects stored in Redis DB 8
(per ``Config.CACHE``), same keys and TTLs as before. The client is lazy, so
importing this module does not require Redis to be reachable.

``redis.asyncio`` offers a drop-in async client for the Phase 3 async work.
"""

import pickle

import redis

from tipi_backend.settings import Config

_cfg = Config.CACHE
_client = redis.Redis(
    host=_cfg["CACHE_REDIS_HOST"],
    port=_cfg["CACHE_REDIS_PORT"],
    password=_cfg["CACHE_REDIS_PASSWORD"] or None,
    db=_cfg["CACHE_REDIS_DB"],
)


def get(key):
    raw = _client.get(key)
    return None if raw is None else pickle.loads(raw)


def set(key, value, timeout=None):
    _client.set(key, pickle.dumps(value), ex=timeout)
