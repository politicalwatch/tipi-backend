"""Tier-1 tests for the sessions + speeches browse endpoints — no Mongo.

The repositories are replaced with in-memory fakes so query-building, pagination meta
and the compact-vs-extended serialization are exercised end to end through the real
business functions and routes.
"""

import pytest

from tipi_data import DoesNotExist
from tipi_data.models.session import Session
from tipi_data.models.speech import Speech

from tipi_backend.api import business

pytestmark = pytest.mark.unit


# ---- query building / pagination (pure) --------------------------------------------

def test_build_speeches_query_maps_every_filter():
    query = business._build_speeches_query(
        {
            "session": "sess1",
            "reference": "172/000001",
            "mention": "nunez-feijoo-alberto",
            "speaker": "Montero Cuadrado, María Jesús",
            "group": "GS",
            "legislature": "15",
            "startdate": "2024-01-01",  # ISO tolerated
            "enddate": "20240301",
        }
    )
    assert query == {
        "session_id": "sess1",
        "references": "172/000001",
        "mentions.person_id": "nunez-feijoo-alberto",
        "speaker": "Montero Cuadrado, María Jesús",
        "group": "GS",
        "legislature": "15",
        "date": {"$gte": 20240101, "$lte": 20240301},
    }


def test_build_sessions_query_empty_and_filtered():
    assert business._build_sessions_query({}) == {}
    assert business._build_sessions_query(
        {"legislature": "15", "code": "DSCD-15-PL-13", "enddate": "20240301"}
    ) == {"legislature": "15", "code": "DSCD-15-PL-13", "date": {"$lte": 20240301}}


def test_pagination_math():
    assert business._pagination(45, 2, 20) == (3, 20, 20)
    assert business._pagination(0, 1, 20) == (0, 20, 0)
    assert business._pagination(10, 1, -1) == (1, None, None)


# ---- fakes + route behavior --------------------------------------------------------

class _FakeSpeeches:
    def __init__(self, docs):
        self.docs = docs

    def count_by_query(self, query):
        return len(self.docs)

    def by_query_paginated(self, query, limit=None, skip=None):
        return self.docs

    def get(self, id):
        for d in self.docs:
            if d.id == id:
                return d
        raise DoesNotExist(id)

    def get_by_video_id(self, video_id):
        for d in self.docs:
            if d.video_id == video_id:
                return d
        raise DoesNotExist(video_id)


class _FakeSessions(_FakeSpeeches):
    pass


def _speech():
    return Speech(
        _id="sp1", references=["R1"], session_id="s1", speaker="X, Y", order=1,
        speech=[{"lang": "es", "text": "hola", "original": True}],
        mentions=[{"person_id": "p1", "person_type": "deputy", "name": "P Uno",
                   "surface_forms": ["Uno"], "count": 1}],
    )


def test_list_speeches_is_compact_with_meta(client, monkeypatch):
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([_speech()]))
    body = client.get("/speeches/?session=s1").json()
    assert body["query_meta"] == {"total": 1, "pages": 1, "page": 1, "per_page": 20}
    item = body["speeches"][0]
    assert item["id"] == "sp1"
    assert item["mentions"][0]["person_id"] == "p1"
    assert "speech" not in item  # compact list omits the text blocks


def test_get_speech_detail_has_text_blocks(client, monkeypatch):
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([_speech()]))
    item = client.get("/speeches/sp1").json()
    assert [b["lang"] for b in item["speech"]] == ["es"]


def test_get_speech_missing_returns_404(client, monkeypatch):
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([]))
    assert client.get("/speeches/nope").status_code == 404


def test_get_speech_by_video_id(client, monkeypatch):
    speech = _speech()
    speech.video_id = "752062"
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([speech]))
    # an all-digits id resolves through the Congress intervention id
    assert client.get("/speeches/752062").json()["id"] == "sp1"
    # the internal id keeps working
    assert client.get("/speeches/sp1").json()["id"] == "sp1"


def test_get_speech_numeric_falls_back_to_internal_id(client, monkeypatch):
    # a pre-video speech whose internal id happens to be all digits
    speech = _speech()
    speech.id = "123456"
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([speech]))
    assert client.get("/speeches/123456").json()["id"] == "123456"

    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([]))
    assert client.get("/speeches/999999").status_code == 404


def test_session_detail_carries_roster_and_count(client, monkeypatch):
    session = Session(_id="s1", legislature="15", name="Pleno",
                      references=["R1", "R2"])
    monkeypatch.setattr(business, "Sessions", _FakeSessions([session]))
    monkeypatch.setattr(business, "Speeches", _FakeSpeeches([_speech(), _speech()]))
    item = client.get("/sessions/s1").json()
    assert item["references"] == ["R1", "R2"]
    assert item["speeches_count"] == 2


def test_list_sessions_has_meta_and_no_count(client, monkeypatch):
    session = Session(_id="s1", legislature="15", references=["R1"])
    monkeypatch.setattr(business, "Sessions", _FakeSessions([session]))
    body = client.get("/sessions/").json()
    assert body["query_meta"]["total"] == 1
    # list items don't compute the per-session speech count
    assert "speeches_count" not in body["sessions"][0]
