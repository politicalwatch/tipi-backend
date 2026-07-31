"""Tier-1 tests for the two cached list endpoints — no Mongo, no Redis.

Since the engine invalidates these keys when it rewrites the data, the responses are
cached with **no expiry**. That removes the 1h TTL that used to quietly repair two
things, so both are pinned here: every response variant needs its own key, and a
filtered response must never be stored under the key the whole list is read from.
"""

import pytest

from tipi_backend.api import cache
from tipi_backend.api.endpoints import deputies as deputies_endpoint
from tipi_backend.api.endpoints import parliamentarygroups as groups_endpoint

pytestmark = pytest.mark.unit


class _FakeCache(dict):
    """An in-memory stand-in for Redis that also remembers the expiry each key
    was set with."""

    def __init__(self):
        super().__init__()
        self.expiries = {}


@pytest.fixture
def fake_cache(monkeypatch):
    store = _FakeCache()

    def set(key, value, timeout=None):
        store[key] = value
        store.expiries[key] = timeout

    monkeypatch.setattr(cache, "get", store.get)
    monkeypatch.setattr(cache, "set", set)
    return store


@pytest.fixture
def lists(monkeypatch):
    """Make both list endpoints echo the query they were called with, so a cached
    response can be traced back to the request that produced it."""
    def fake(module, name):
        monkeypatch.setattr(module, name, lambda params: [{"echo": dict(params)}])

    fake(deputies_endpoint, "get_deputies")
    fake(groups_endpoint, "get_parliamentarygroups")


# --- cached until invalidated, never expired ----------------------------------

@pytest.mark.parametrize("path,key", [
    ("/deputies/", "deputies"),
    ("/parliamentary-groups/", "parliamentary-groups"),
])
def test_lists_are_cached_without_an_expiry(client, fake_cache, lists, path, key):
    client.get(path)

    assert key in fake_cache
    # None => Redis SET with no EX: the engine's invalidation is what clears it.
    assert fake_cache.expiries[key] is None


@pytest.mark.parametrize("path,key", [
    ("/deputies/", "deputies"),
    ("/parliamentary-groups/", "parliamentary-groups"),
])
def test_a_cached_list_is_served_back(client, fake_cache, lists, path, key):
    fake_cache[key] = [{"echo": "from cache"}]

    assert client.get(path).json() == [{"echo": "from cache"}]


# --- one key per variant ------------------------------------------------------

@pytest.mark.parametrize("path,full_key,compact_key", [
    ("/deputies/", "deputies", "deputies-compact"),
    ("/parliamentary-groups/", "parliamentary-groups",
     "parliamentary-groups-compact"),
])
def test_compact_never_lands_on_the_full_key(client, fake_cache, lists,
                                             path, full_key, compact_key):
    # qhld-widget asks for the compact groups while qhld.es asks for the full
    # list; with one shared key the first caller's variant served both.
    client.get(f"{path}?compact=true")

    assert fake_cache[compact_key][0]["echo"]["compact"] is True
    assert full_key not in fake_cache


# --- filtered responses stay out of the cache --------------------------------

@pytest.mark.parametrize("path,key", [
    ("/deputies/", "deputies"),
    ("/parliamentary-groups/", "parliamentary-groups"),
])
def test_a_name_filter_neither_reads_nor_writes_the_cache(client, fake_cache,
                                                          lists, path, key):
    body = client.get(f"{path}?name=Sánchez").json()

    assert body[0]["echo"]["name"] == "Sánchez"
    assert fake_cache == {}


@pytest.mark.parametrize("path,key", [
    ("/deputies/", "deputies"),
    ("/parliamentary-groups/", "parliamentary-groups"),
])
def test_a_filtered_request_does_not_poison_the_full_list(client, fake_cache,
                                                          lists, path, key):
    client.get(f"{path}?name=Sánchez")
    body = client.get(path).json()

    assert body[0]["echo"].get("name") is None
    assert fake_cache[key] == body
