"""Tier-1 tests for the subtitle track a player loads — no Mongo.

The cues live in their own collection and carry character offsets rather than text,
so what these cover is the join: the track is rendered from the offsets over the
stored transcript, and it is withheld whenever that transcript is no longer the one
the cues were made against.
"""

import pytest

from tipi_data import DoesNotExist
from tipi_data.models.speech import Speech
from tipi_data.models.speech_alignment import Cue, SpeechAlignment

from qhld_ai.domain.subtitles import text_fingerprint

from tipi_backend.api import business

pytestmark = pytest.mark.unit


TEXT = "Muchas gracias, presidente. He escuchado con atención."


def _speech(text=TEXT, lang="es"):
    return Speech(
        _id="sp1", video_id="726567", references=["R1"], session_id="s1",
        speaker="Saiz Delgado, Elma", order=1,
        speech=[{"lang": lang, "text": text, "original": True}],
    )


def _alignment(text=TEXT, lang="es"):
    digest, length = text_fingerprint(text)
    return SpeechAlignment(
        _id="sp1", lang=lang, block_index=0,
        cues=[Cue(start_ms=3420, end_ms=7180, char_start=0, char_end=27),
              Cue(start_ms=7180, end_ms=11000, char_start=28, char_end=54)],
        text_sha256=digest, text_length=length, score=97.0, verdict="ok")


class _FakeSpeeches:
    def __init__(self, docs):
        self.docs = docs

    def get(self, id):
        for doc in self.docs:
            if doc.id == id:
                return doc
        raise DoesNotExist(id)

    def get_by_video_id(self, video_id):
        for doc in self.docs:
            if doc.video_id == video_id:
                return doc
        raise DoesNotExist(video_id)


class _FakeAlignments:
    def __init__(self, alignment=None):
        self.alignment = alignment

    def summary(self, id):
        if self.alignment is None:
            return None
        return {k: v for k, v in self.alignment.to_bson().items() if k != "cues"}

    def get(self, id):
        if self.alignment is None:
            raise DoesNotExist(id)
        return self.alignment


def _corpus(monkeypatch, speech=None, alignment=None):
    monkeypatch.setattr(business, "Speeches",
                        _FakeSpeeches([speech or _speech()]))
    monkeypatch.setattr(business, "SpeechAlignments", _FakeAlignments(alignment))


# ---- the track ---------------------------------------------------------------------

def test_track_is_webvtt_with_the_transcript_sliced_in(client, monkeypatch):
    _corpus(monkeypatch, alignment=_alignment())

    response = client.get("/speeches/sp1/subtitles.vtt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vtt")
    assert response.text.startswith("WEBVTT\n\n")
    assert "00:00:03.420 --> 00:00:07.180" in response.text
    assert "Muchas gracias, presidente." in response.text


def test_track_is_cacheable(client, monkeypatch):
    _corpus(monkeypatch, alignment=_alignment())

    response = client.get("/speeches/sp1/subtitles.vtt")

    assert "max-age" in response.headers["cache-control"]


def test_track_by_congress_intervention_id(client, monkeypatch):
    # The public URLs are keyed on the video id, so that is what a player asks for.
    _corpus(monkeypatch, alignment=_alignment())

    assert client.get("/speeches/726567/subtitles.vtt").status_code == 200


def test_track_of_an_unaligned_speech_is_404(client, monkeypatch):
    _corpus(monkeypatch)

    assert client.get("/speeches/sp1/subtitles.vtt").status_code == 404


def test_track_of_an_unknown_speech_is_404(client, monkeypatch):
    _corpus(monkeypatch, alignment=_alignment())

    assert client.get("/speeches/nope/subtitles.vtt").status_code == 404


def test_track_is_withheld_when_the_transcript_has_changed(client, monkeypatch):
    # Offsets into a re-cleaned transcript are not stale but wrong — they would
    # caption one sentence with another. No subtitles is the safe answer.
    _corpus(monkeypatch, speech=_speech(text="Otro texto distinto por completo."),
            alignment=_alignment())

    assert client.get("/speeches/sp1/subtitles.vtt").status_code == 404


def test_subtitles_route_does_not_shadow_the_speech_itself(client, monkeypatch):
    _corpus(monkeypatch, alignment=_alignment())

    assert client.get("/speeches/sp1").json()["id"] == "sp1"


# ---- the detail payload's indicator ------------------------------------------------

def test_detail_says_which_language_the_track_is_in(client, monkeypatch):
    _corpus(monkeypatch, speech=_speech(lang="gl"),
            alignment=_alignment(lang="gl"))

    assert client.get("/speeches/sp1").json()["subtitles"] == {"lang": "gl"}


def test_detail_omits_subtitles_when_there_are_none(client, monkeypatch):
    _corpus(monkeypatch)

    assert "subtitles" not in client.get("/speeches/sp1").json()


def test_detail_omits_subtitles_the_track_would_refuse_to_serve(client, monkeypatch):
    # The page must never advertise a track that 404s on request.
    _corpus(monkeypatch, speech=_speech(text="Otro texto distinto por completo."),
            alignment=_alignment())

    assert "subtitles" not in client.get("/speeches/sp1").json()
