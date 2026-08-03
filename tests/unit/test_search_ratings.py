"""Tier-1 tests for POST /search-ratings — no Mongo, no Redis.

``save_search_rating`` (the only Mongo write behind the route) is monkeypatched out, so
these isolate the two things the endpoint actually owns: the shared-secret gate that
makes "came through our frontend" enforceable without user accounts, and the rate limit.

Note the token is read via ``get_settings()`` *inside* the dependency, which is what lets
``monkeypatch.setenv`` work against the session-scoped app built by the ``client``
fixture; and that ``os.environ`` wins over the repo ``.env``, so setting it to "" here
really does exercise the unconfigured case.
"""

import pytest

pytestmark = pytest.mark.unit

TOKEN = "s3cret-token"
HEADERS = {"X-QHLD-Token": TOKEN}


def payload(**overrides):
    body = {
        "rating": 2,
        "query": "intervenciones de Tesh Sidi sobre el Sáhara",
        "query_meta": {
            "semantic_query": "Sáhara",
            "unresolved": [
                {"field": "speaker", "value": "Tesh Sidi", "blocking": True}
            ],
        },
        "reasons": ["persona_no_reconocida"],
        "comment": "No encuentra a esta diputada",
        "result_ids": ["sp-1", "sp-2"],
        "corpus": "2026-08-03T04:12:00",
    }
    body.update(overrides)
    return body


@pytest.fixture
def saved(monkeypatch):
    """Capture what reached the business layer instead of writing to Mongo."""
    calls = []
    monkeypatch.setenv("SEARCH_RATING_TOKEN", TOKEN)
    monkeypatch.setattr(
        "tipi_backend.api.endpoints.search_ratings.save_search_rating",
        lambda body: calls.append(body),
    )
    return calls


def test_valid_token_is_accepted(client, saved):
    res = client.post("/search-ratings", json=payload(), headers=HEADERS)

    assert res.status_code == 201
    assert res.json() == {"status": "ok"}
    assert len(saved) == 1
    # query_meta is passed through untouched — `unresolved` is the whole point of
    # storing it, and re-modelling it here would flatten it.
    assert saved[0]["query_meta"]["unresolved"][0]["value"] == "Tesh Sidi"
    assert saved[0]["reasons"] == ["persona_no_reconocida"]


def test_missing_token_is_rejected(client, saved):
    res = client.post("/search-ratings", json=payload())

    # 401, not the 400 a required Header() would produce via RequestValidationError.
    assert res.status_code == 401
    assert saved == []


def test_wrong_token_is_rejected(client, saved):
    res = client.post(
        "/search-ratings", json=payload(), headers={"X-QHLD-Token": "not-the-token"}
    )

    assert res.status_code == 401
    assert saved == []


def test_unconfigured_token_fails_closed(client, monkeypatch):
    """No configured secret means we cannot tell our frontend from anyone else, so
    every rating is refused — a misconfigured deploy must not accept anonymous writes."""
    calls = []
    monkeypatch.setenv("SEARCH_RATING_TOKEN", "")
    monkeypatch.setattr(
        "tipi_backend.api.endpoints.search_ratings.save_search_rating",
        lambda body: calls.append(body),
    )

    res = client.post("/search-ratings", json=payload(), headers=HEADERS)

    assert res.status_code == 401
    assert calls == []


@pytest.mark.parametrize(
    "bad",
    [
        {"rating": 0},
        {"rating": 6},
        {"rating": "muy bueno"},
        {"query": ""},
        {"comment": "x" * 501},
        {"result_ids": ["sp"] * 101},
    ],
)
def test_malformed_body_is_a_400(client, saved, bad):
    res = client.post("/search-ratings", json=payload(**bad), headers=HEADERS)

    # The app remaps RequestValidationError to 400 (flask-restx parity), not FastAPI's
    # default 422.
    assert res.status_code == 400
    assert saved == []


def test_rating_is_required(client, saved):
    body = payload()
    del body["rating"]

    assert client.post("/search-ratings", json=body, headers=HEADERS).status_code == 400
    assert saved == []


def test_rate_limit_caps_the_collection(client, saved):
    """A blast-radius cap, not a per-user limit: every rating arrives through the Nuxt
    server, so slowapi sees one IP for the whole audience. The per-client limit lives in
    the nitro route."""
    for _ in range(600):
        assert client.post(
            "/search-ratings", json=payload(), headers=HEADERS
        ).status_code == 201

    res = client.post("/search-ratings", json=payload(), headers=HEADERS)

    assert res.status_code == 429
