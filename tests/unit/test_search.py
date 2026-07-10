"""Tier-1 tests for the semantic search endpoint — no Mongo, no Qdrant, no LLM.

The qhld-ai service is replaced with a spy (canned ``SpeechGroup``s) and the
Speeches repository with an in-memory fake, so the exclude/has_more/hydration
logic and the response envelope are exercised end to end through the real
business function and route.
"""

from datetime import date

import pytest

from qhld_ai.application.search.natural_search import NaturalResult
from qhld_ai.application.search.resolve_entities import Resolution, UnresolvedEntity
from qhld_ai.domain.ports.query_parser import ParsedQuery
from qhld_ai.domain.ports.vector_store import SearchHit, SpeechGroup

from tipi_data.models.speech import Speech

from tipi_backend.api import business

pytestmark = pytest.mark.unit


def _speech(id):
    return Speech(
        _id=id, references=["R1"], session_id="s1", speaker="X, Y", order=1,
        speech=[{"lang": "es", "text": "hola", "original": True}],
    )


def _group(speech_id, score=0.9, passages=("un pasaje",)):
    return SpeechGroup(
        speech_id=speech_id, score=score,
        highlights=[SearchHit(id=f"{speech_id}-{i}", score=score, payload={"text": p})
                    for i, p in enumerate(passages)])


class _SpyParser:
    def __init__(self):
        self.calls = 0

    def parse(self, q, today):
        self.calls += 1
        return ParsedQuery(semantic_query="vivienda")


class _SpyService:
    """Stands in for NaturalSearchSpeeches: records execute() kwargs, returns
    canned groups (trimmed to k, honoring exclude, like the real grouped search)."""

    def __init__(self, groups, resolution=None):
        self.groups = groups
        self.resolution = resolution or Resolution()
        self.parser = _SpyParser()
        self.calls = []

    def execute(self, query, today, k=10, grouped=False, highlights=3,
                exclude=None, parsed=None):
        self.calls.append({"query": query, "today": today, "k": k,
                           "grouped": grouped, "highlights": highlights,
                           "exclude": exclude, "parsed": parsed})
        if self.resolution.blocked:
            return NaturalResult(parsed=parsed, resolution=self.resolution,
                                 semantic_query="vivienda", grouped=grouped)
        hits = [g for g in self.groups if not (exclude and g.speech_id in exclude)][:k]
        return NaturalResult(parsed=parsed, resolution=self.resolution,
                             semantic_query="vivienda", hits=hits, grouped=grouped)


class _FakeSpeeches:
    def __init__(self, docs):
        self.docs = {d.id: d for d in docs}

    def by_query_paginated(self, query, limit=None, skip=None):
        return [self.docs[i] for i in query["_id"]["$in"] if i in self.docs]


@pytest.fixture(autouse=True)
def _fresh_caches():
    business._natural_search.cache_clear()
    business._parse_query.cache_clear()
    yield
    business._natural_search.cache_clear()
    business._parse_query.cache_clear()


def _install(monkeypatch, service, speech_ids=None):
    monkeypatch.setattr(business, "_natural_search", lambda: service)
    ids = speech_ids if speech_ids is not None else [g.speech_id for g in service.groups]
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([_speech(i) for i in ids]))
    return service


def test_response_envelope_and_relevance_order(client, monkeypatch):
    # Mongo's fake returns docs in query order, but the endpoint must keep
    # Qdrant's score order even if hydration returns them differently.
    service = _install(monkeypatch, _SpyService(
        [_group("sp2", 0.9, ("mejor pasaje", "otro")), _group("sp1", 0.7)]))
    body = client.get("/speeches/search?q=vivienda joven&per_page=12").json()
    assert body["query_meta"]["q"] == "vivienda joven"
    assert body["query_meta"]["semantic_query"] == "vivienda"
    assert body["query_meta"]["count"] == 2
    assert body["query_meta"]["has_more"] is False
    assert [r["speech"]["id"] for r in body["results"]] == ["sp2", "sp1"]
    assert body["results"][0]["score"] == 0.9
    assert body["results"][0]["highlights"] == ["mejor pasaje", "otro"]
    assert "speech" not in body["results"][0]["speech"]  # compact card, no text blocks
    call = service.calls[0]
    assert call["grouped"] is True
    assert call["k"] == 13  # per_page + 1: the has_more probe
    assert call["today"] == date.today()


def test_has_more_when_probe_group_comes_back(client, monkeypatch):
    _install(monkeypatch, _SpyService([_group(f"sp{i}") for i in range(3)]))
    body = client.get("/speeches/search?q=vivienda&per_page=2").json()
    assert body["query_meta"]["has_more"] is True
    assert body["query_meta"]["count"] == 2
    assert len(body["results"]) == 2


def test_exclude_is_forwarded_as_a_set(client, monkeypatch):
    service = _install(monkeypatch, _SpyService([_group("sp3")]))
    body = client.get("/speeches/search?q=vivienda&exclude=sp1&exclude=sp2").json()
    assert service.calls[0]["exclude"] == {"sp1", "sp2"}
    assert [r["speech"]["id"] for r in body["results"]] == ["sp3"]


def test_parse_is_cached_across_show_more_clicks(client, monkeypatch):
    service = _install(monkeypatch, _SpyService([_group("sp1")]))
    client.get("/speeches/search?q=vivienda")
    client.get("/speeches/search?q=vivienda&exclude=sp1")
    assert service.parser.calls == 1  # one LLM parse, reused by the second click
    assert all(c["parsed"] is not None for c in service.calls)


def test_blocked_resolution_yields_honest_zero_with_meta(client, monkeypatch):
    resolution = Resolution(unresolved=[
        UnresolvedEntity("mentions", "Santiago Segura", blocking=True,
                         suggestion="Santiago Abascal")])
    _install(monkeypatch, _SpyService([], resolution=resolution), speech_ids=[])
    body = client.get("/speeches/search?q=que mencionen a Santiago Segura").json()
    assert body["results"] == []
    assert body["query_meta"]["has_more"] is False
    assert body["query_meta"]["unresolved"] == [
        {"field": "mentions", "value": "Santiago Segura", "blocking": True,
         "suggestion": "Santiago Abascal"}]


def test_speech_missing_from_mongo_is_skipped(client, monkeypatch):
    _install(monkeypatch, _SpyService([_group("sp1"), _group("gone")]),
             speech_ids=["sp1"])
    body = client.get("/speeches/search?q=vivienda").json()
    assert [r["speech"]["id"] for r in body["results"]] == ["sp1"]
    assert body["query_meta"]["count"] == 1


def test_service_failure_returns_503(client, monkeypatch):
    def _boom():
        raise RuntimeError("qdrant down")
    monkeypatch.setattr(business, "_natural_search", _boom)
    assert client.get("/speeches/search?q=vivienda").status_code == 503


def test_validation_missing_q_and_caps(client):
    assert client.get("/speeches/search").status_code == 400
    assert client.get("/speeches/search?q=a").status_code == 400        # min_length=2
    assert client.get("/speeches/search?q=ok&per_page=51").status_code == 400
    assert client.get("/speeches/search?q=ok&highlights=11").status_code == 400
