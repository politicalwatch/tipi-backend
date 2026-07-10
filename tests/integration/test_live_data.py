"""Tier-2 live-data smoke tests (``-m integration``).

These pin the **connection + data contract** against qhld-infra's prod-copy Mongo —
read-only, never mutating. They are intentionally separate from the Tier-1 endpoint
tests so a Mongo/data problem fails *here*, not in the tagger logic tests.

Run with ``MONGO_*`` pointing at the prod copy, e.g. from the host:
    MONGO_HOST=localhost MONGO_PORT=62884 MONGO_USER=qhld MONGO_PASSWORD=… \
        uv run pytest -m integration
or inside the qhld-infra ``qhld-backend`` container (``MONGO_HOST=mongo``).
"""

import os

import pytest

from tipi_data import db
from tipi_data.repositories.knowledgebases import KnowledgeBases

from tipi_backend.api.business import get_tags, get_topics

pytestmark = pytest.mark.integration

STABLE_KBS = {"politicas", "ods"}


def test_get_tags_live_wellformed():
    tags = get_tags()
    assert tags, "live KB returned no tags"
    sample = tags[0]
    assert {"topic", "subtopic", "tag", "knowledgebase", "public", "compiletag"} <= sample.keys()


def test_public_knowledgebases_include_stable():
    kbs = set(KnowledgeBases.get_public())
    assert STABLE_KBS <= kbs, f"expected {STABLE_KBS} among public KBs, got {kbs}"


def test_public_topics_present():
    assert get_topics(), "no public topics in live DB"


@pytest.mark.parametrize("collection", ["topics", "deputies", "parliamentarygroups", "initiatives"])
def test_core_collections_nonempty(collection):
    assert db[collection].estimated_document_count() > 0, f"{collection} is empty"


def test_sessions_and_speeches_endpoints_live(client):
    """End-to-end shape check through the routes against prod-copy data: session
    listing → detail (count + roster) → its speeches (compact) → a speech in full."""
    if db.sessions.estimated_document_count() == 0:
        pytest.skip("no sessions in the live DB yet")

    listing = client.get("/sessions/?per_page=3").json()
    assert listing["query_meta"]["total"] > 0
    session = listing["sessions"][0]
    assert session["id"] and "references" in session

    detail = client.get(f"/sessions/{session['id']}").json()
    assert "speeches_count" in detail

    speeches = client.get(f"/speeches/?session={session['id']}").json()
    assert speeches["query_meta"]["total"] == detail["speeches_count"]
    if speeches["speeches"]:
        first = speeches["speeches"][0]
        assert "speech" not in first  # compact list
        full = client.get(f"/speeches/{first['id']}").json()
        assert "speech" in full  # detail carries the text blocks


def test_speech_missing_returns_404(client):
    assert client.get("/speeches/does-not-exist").status_code == 404


def test_semantic_search_live_show_more(client):
    """Smoke the full search stack (LLM parse → Qdrant grouped search → Mongo
    hydration): distinct speeches per page, and an excluded second page that
    doesn't repeat the first. Needs Qdrant + provider keys besides Mongo."""
    if db.speeches.estimated_document_count() == 0:
        pytest.skip("no speeches in the live DB yet")
    if not (os.environ.get("OPENAI_API_KEY") and os.environ.get("ANTHROPIC_API_KEY")):
        pytest.skip("AI provider keys not configured")

    first = client.get("/speeches/search?q=vivienda&per_page=5")
    if first.status_code == 503:
        pytest.skip("search stack unreachable (Qdrant/embedding provider)")
    body = first.json()
    assert body["query_meta"]["semantic_query"]
    ids = [r["speech"]["id"] for r in body["results"]]
    assert len(ids) == len(set(ids)), "grouping must yield distinct speeches"
    for result in body["results"]:
        assert result["highlights"], "every result should carry passages"

    if body["query_meta"]["has_more"] and ids:
        exclude = "&".join(f"exclude={i}" for i in ids)
        more = client.get(f"/speeches/search?q=vivienda&per_page=5&{exclude}").json()
        assert not set(ids) & {r["speech"]["id"] for r in more["results"]}, \
            "show more must not repeat already-shown speeches"
