"""Tier-1 tests for the intent-gate ban — no Redis, no network.

The Redis client in ``api.bans`` is replaced with a fake that implements the four
commands the module uses (``incr``, ``expire``, ``ttl``, ``setex``) plus a pipeline that
buffers and replays them. That is enough to exercise every decision, and it keeps these
tests runnable with no infrastructure.
"""

from types import SimpleNamespace

import pytest

from tipi_backend.api import bans

pytestmark = pytest.mark.unit


class _FakePipeline:
    def __init__(self, store):
        self.store = store
        self.queued = []

    def incr(self, key):
        self.queued.append(("incr", key, None))
        return self

    def expire(self, key, seconds, nx=False):
        self.queued.append(("expire", key, seconds))
        return self

    def execute(self):
        results = []
        for command, key, seconds in self.queued:
            if command == "incr":
                self.store.counts[key] = self.store.counts.get(key, 0) + 1
                results.append(self.store.counts[key])
            else:
                # NX semantics: the first refusal in a window sets the expiry and later
                # ones leave it alone, which is what stops a steady prober from pushing
                # the window forward forever.
                results.append(self.store.expiries.setdefault(key, seconds))
        self.queued = []
        return results


class _FakeRedis:
    def __init__(self):
        self.counts = {}
        self.expiries = {}
        self.bans = {}

    def pipeline(self):
        return _FakePipeline(self)

    def ttl(self, key):
        return self.bans.get(key, -2)

    def setex(self, key, seconds, value):
        self.bans[key] = seconds


class _BrokenRedis(_FakeRedis):
    def pipeline(self):
        raise RuntimeError("redis down")

    def ttl(self, key):
        raise RuntimeError("redis down")


def _request(host="203.0.113.7"):
    return SimpleNamespace(client=SimpleNamespace(host=host), headers={})


@pytest.fixture
def store(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(bans, "_client", fake)
    return fake


def _configure(monkeypatch, mode="enforce", forwarded="10.0.0.1", tiers=None):
    monkeypatch.setattr(bans, "_settings", SimpleNamespace(
        search_ban_mode=mode,
        forwarded_allow_ips=forwarded,
        cache_redis_host="redis", cache_redis_port=6379,
        cache_redis_password="", ban_redis_db=9,
        ban_tiers=tiers or {3600: (5, 900), 86400: (15, 21600)},
    ))


def test_a_tier_bans_only_once_it_is_crossed(monkeypatch, store):
    _configure(monkeypatch)
    request = _request()

    # Four refusals sit under the hourly allowance of five.
    for _ in range(4):
        assert bans.record_refusal(request, "not_a_speech_search") == 0
    assert bans.banned_for(request) == 0

    assert bans.record_refusal(request, "not_a_speech_search") == 900
    assert bans.banned_for(request) == 900


def test_the_longest_tier_crossed_is_the_one_applied(monkeypatch, store):
    # An actor over the daily allowance is necessarily over the hourly one too, and the
    # hourly answer is not the interesting one.
    _configure(monkeypatch, tiers={3600: (5, 900), 86400: (8, 21600)})
    request = _request()

    bans_decided = [bans.record_refusal(request, "not_a_speech_search")
                    for _ in range(8)]

    assert bans_decided[4] == 900       # hourly tier first
    assert bans_decided[7] == 21600     # daily tier takes over once crossed
    assert bans.banned_for(request) == 21600


def test_a_language_refusal_never_counts(monkeypatch, store):
    _configure(monkeypatch)
    request = _request()

    for _ in range(20):
        assert bans.record_refusal(request, "unsupported_language") == 0

    # Someone asking real questions in Portuguese is not an attacker, and the language
    # verdict has its own uncertainty — this must not be a slow path to a ban.
    assert bans.banned_for(request) == 0
    assert store.counts == {}


def test_addresses_are_counted_apart(monkeypatch, store):
    _configure(monkeypatch)

    for _ in range(5):
        bans.record_refusal(_request("203.0.113.7"), "not_a_speech_search")

    assert bans.banned_for(_request("203.0.113.7")) == 900
    assert bans.banned_for(_request("198.51.100.4")) == 0


def test_shadow_mode_decides_but_does_not_ban(monkeypatch, store, caplog):
    _configure(monkeypatch, mode="shadow")
    request = _request()

    decided = [bans.record_refusal(request, "not_a_speech_search") for _ in range(5)]

    # The verdict is real — that is what makes the logs worth reading — but nothing is
    # stored, so the next request is served.
    assert decided[-1] == 900
    assert bans.banned_for(request) == 0
    assert store.bans == {}
    assert "WOULD ban" in caplog.text


def test_enforcement_refuses_while_the_address_is_caller_controlled(monkeypatch, store,
                                                                    caplog):
    # With FORWARDED_ALLOW_IPS at "*" uvicorn takes the leftmost X-Forwarded-For entry,
    # which the caller writes. Banning on it would miss anyone rotating the header and
    # land on whoever they named instead.
    _configure(monkeypatch, mode="enforce", forwarded="*")
    request = _request()

    for _ in range(5):
        bans.record_refusal(request, "not_a_speech_search")

    assert bans.enforcing() is False
    assert bans.banned_for(request) == 0
    assert "caller-controlled" in caplog.text


def test_off_records_nothing_at_all(monkeypatch, store):
    _configure(monkeypatch, mode="off")
    request = _request()

    assert bans.record_refusal(request, "not_a_speech_search") == 0
    assert bans.banned_for(request) == 0
    assert store.counts == {}


def test_a_broken_store_serves_the_request(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(bans, "_client", _BrokenRedis())
    request = _request()

    # Bookkeeping being down must not ban anyone, and must not turn a search into a 500.
    assert bans.record_refusal(request, "not_a_speech_search") == 0
    assert bans.banned_for(request) == 0
    assert bans.reject_if_banned(request) is None


def test_the_ban_response_carries_a_usable_retry_after(monkeypatch, store):
    _configure(monkeypatch)
    request = _request()
    for _ in range(5):
        bans.record_refusal(request, "not_a_speech_search")

    response = bans.reject_if_banned(request)

    assert response.status_code == 429
    # Floored at 1 like the limiter's: "retry after zero seconds" reads as "retry now".
    assert int(response.headers["Retry-After"]) >= 1


def test_a_window_expiry_is_not_pushed_forward_by_later_refusals(monkeypatch, store):
    _configure(monkeypatch)
    request = _request()

    for _ in range(3):
        bans.record_refusal(request, "not_a_speech_search")

    # One expiry per window, set by the FIRST refusal in it. Renewing on every refusal
    # would let an address that keeps probing hold its counter open indefinitely and
    # never age out of a window it is sitting just under.
    assert set(store.expiries.values()) == {3600, 86400}
