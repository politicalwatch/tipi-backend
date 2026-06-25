"""Tier-1 tagger endpoint tests — no Mongo, no Redis, no broker.

The tagging *algorithm* lives in qhld-tasks (its own suite). These tests pin the
**endpoint's** behavior: KB load → sync/async branching → ``filter_tags`` /
``remove_fields``. The KB is injected through ``cache.get`` from a self-contained
fixture, and ``knowledgebase`` is passed explicitly so ``get_kbs`` never hits Mongo.
"""

import pytest

from tipi_backend.settings import Config
from tests.helpers import (
    build_tags_from_fixture,
    load_knowledgebase,
    read_scanner_text,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="session")
def kb_tags():
    """The compiled tag list (with ``compiletag`` regexes), built once per session."""
    return build_tags_from_fixture(load_knowledgebase())


@pytest.fixture(autouse=True)
def inject_tags(monkeypatch, kb_tags):
    """Serve the fixture KB from the cache so ``get_tags()`` / Mongo are never hit."""
    monkeypatch.setattr("tipi_backend.api.cache.get", lambda key: kb_tags)


@pytest.fixture
def sync_word_limit(monkeypatch):
    """Keep every scanner_text fixture in the synchronous tagging path."""
    monkeypatch.setattr(Config, "TAGGER_MAX_WORDS", 6000)


# One high-confidence (topic, tag) pair per fixture — a sanity anchor that the fixture
# KB still produces obvious hits. Derived empirically (highest match counts), kept to a
# known *subset* so it isn't brittle. NOT an exhaustive list (that would re-test the
# qhld-tasks algorithm, which owns its own suite).
SANITY_HITS = {
    "w100.txt": ("ODS 16 Paz, justicia e instituciones sólidas", "Elusión y evasión fiscal"),
    "w500.txt": ("ODS 3 Salud y bienestar", "Aborto"),
    "w1000.txt": ("ODS 17 Alianzas para lograr los objetivos", "Estrategia de Desarrollo Sostenible"),
    "w2000.txt": ("ODS 13 Acción por el clima", "Cambio climático"),
    "w5000.txt": ("Personas mayores", "Persona mayor"),
}


@pytest.mark.parametrize("filename", SANITY_HITS)
def test_extract_tags_contract(client, sync_word_limit, filename):
    text = read_scanner_text(filename)

    res = client.post("/tagger/", data={"text": text, "knowledgebase": "politicas,ods"})
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "SUCCESS"
    assert "result" in body

    topics = body["result"]["topics"]
    tags = body["result"]["tags"]
    assert topics, f"{filename}: expected at least one topic"
    assert tags, f"{filename}: expected at least one tag"

    by_topic = {}
    for tag in tags:
        # Schema the endpoint guarantees after filter_tags + remove_fields.
        assert {"topic", "subtopic", "tag", "knowledgebase", "times"} <= tag.keys()
        assert "public" not in tag, "remove_fields should have deleted 'public'"
        assert tag["topic"] in topics, f"tag topic {tag['topic']!r} missing from topics"
        assert tag["knowledgebase"] in ("politicas", "ods")
        by_topic.setdefault(tag["topic"], set()).add(tag["tag"])

    topic, expected_tag = SANITY_HITS[filename]
    assert expected_tag in by_topic.get(topic, set()), (
        f"{filename}: expected sanity hit {expected_tag!r} under topic {topic!r}"
    )


def test_kb_filtering(client, sync_word_limit):
    """`filter_tags` drops tags whose knowledgebase is not requested."""
    text = read_scanner_text("w500.txt")

    res = client.post("/tagger/", data={"text": text, "knowledgebase": "ods"})
    assert res.status_code == 200

    tags = res.json()["result"]["tags"]
    assert tags, "expected at least one ods tag for w500"
    assert all(tag["knowledgebase"] == "ods" for tag in tags), (
        "filtering by 'ods' must exclude every non-ods (e.g. politicas) tag"
    )


def test_null_file_field_falls_back_to_text(client, sync_word_limit):
    """A multipart `file` field carrying the literal string "null" must be ignored.

    Browsers that do ``formData.append('file', null)`` (e.g. escaner2030's scanner
    when no file is chosen) send the *string* ``"null"``. Before the fix this failed
    UploadFile validation and the error handler crashed into a bare 500 (which the
    browser reported as a CORS error). It must now use the text path instead.
    """
    text = read_scanner_text("w500.txt")

    res = client.post(
        "/tagger/",
        data={"text": text, "file": "null", "knowledgebase": "ods"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"


def test_async_dispatch(client, monkeypatch):
    """Texts >= TAGGER_MAX_WORDS are dispatched asynchronously (PROCESSING + task_id).

    The ``memory://`` broker (set in conftest) lets the real ``apply_async`` return a
    task id in-process — no Redis/worker, and the heavy task never actually runs — so
    we exercise the endpoint's genuine *dispatch decision* rather than a mock.
    """
    monkeypatch.setattr(Config, "TAGGER_MAX_WORDS", 10)

    res = client.post(
        "/tagger/", data={"text": "word " * 11, "knowledgebase": "politicas,ods"}
    )
    assert res.status_code == 200

    body = res.json()
    assert body["status"] == "PROCESSING"
    assert isinstance(body["task_id"], str) and body["task_id"]
    assert "estimated_time" in body
