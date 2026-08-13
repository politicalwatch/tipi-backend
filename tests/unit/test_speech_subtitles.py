"""Tier-1 tests for the subtitle tracks a player loads — no Mongo.

The cues live in their own collection, one document per speech and language, and carry
character offsets rather than text. So what these cover is the join: a track is rendered
from the offsets over the stored transcript, the right language is served for the
language asked for, and a track is withheld whenever that transcript is no longer the
one its cues were made against.
"""

import pytest

from tipi_data import DoesNotExist
from tipi_data.models.speech import Speech
from tipi_data.models.speech_alignment import Cue, SpeechAlignment, track_id

from qhld_ai.domain.subtitles import text_fingerprint

from tipi_backend.api import business

pytestmark = pytest.mark.unit


TEXT = "Muchas gracias, presidente. He escuchado con atención."
GALEGO = "Grazas, presidente. Escoitei con atención os seus argumentos."


def _speech(text=TEXT, lang="es", blocks=None):
    return Speech(
        _id="sp1", video_id="726567", references=["R1"], session_id="s1",
        speaker="Saiz Delgado, Elma", order=1,
        speech=blocks or [{"lang": lang, "text": text, "original": True}],
    )


def _bilingual(original=GALEGO, translation=TEXT):
    """A co-official intervention: the original followed by its Spanish reading."""
    return _speech(blocks=[
        {"lang": "gl", "text": original, "original": True},
        {"lang": "es", "text": translation, "original": False},
    ])


def _alignment(text=TEXT, lang="es", block_index=0, original=True):
    digest, length = text_fingerprint(text)
    return SpeechAlignment(
        _id=track_id("sp1", lang, original), speech_id="sp1", lang=lang,
        block_index=block_index, original=original,
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
    """Stands in for the collection, keyed the way the real one is — by language AND
    role, because two blocks of one speech can be the same language."""

    def __init__(self, alignments=()):
        self.by_block = {(a.lang, bool(a.original)): a for a in alignments}

    def summary(self, id, lang, original=True):
        alignment = self.by_block.get((lang, original))
        if alignment is None:
            return None
        return {k: v for k, v in alignment.to_bson().items() if k != "cues"}

    def summaries(self, id, blocks):
        return [s for s in (self.summary(id, lang, original)
                            for lang, original in blocks)
                if s is not None]

    def get(self, id, lang, original=True):
        if (lang, original) not in self.by_block:
            raise DoesNotExist(id)
        return self.by_block[(lang, original)]


def _corpus(monkeypatch, speech=None, alignments=()):
    monkeypatch.setattr(business, "Speeches",
                        _FakeSpeeches([speech or _speech()]))
    monkeypatch.setattr(business, "SpeechAlignments", _FakeAlignments(alignments))


# ---- the track ---------------------------------------------------------------------

def test_track_is_webvtt_with_the_transcript_sliced_in(client, monkeypatch):
    _corpus(monkeypatch, alignments=[_alignment()])

    response = client.get("/speeches/sp1/subtitles.vtt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vtt")
    assert response.text.startswith("WEBVTT\n\n")
    assert "00:00:03.420 --> 00:00:07.180" in response.text
    assert "Muchas gracias, presidente." in response.text


def test_track_is_cacheable(client, monkeypatch):
    _corpus(monkeypatch, alignments=[_alignment()])

    response = client.get("/speeches/sp1/subtitles.vtt")

    assert "max-age" in response.headers["cache-control"]


def test_track_by_congress_intervention_id(client, monkeypatch):
    # The public URLs are keyed on the video id, so that is what a player asks for.
    _corpus(monkeypatch, alignments=[_alignment()])

    assert client.get("/speeches/726567/subtitles.vtt").status_code == 200


def test_track_of_an_unaligned_speech_is_404(client, monkeypatch):
    _corpus(monkeypatch)

    assert client.get("/speeches/sp1/subtitles.vtt").status_code == 404


def test_track_of_an_unknown_speech_is_404(client, monkeypatch):
    _corpus(monkeypatch, alignments=[_alignment()])

    assert client.get("/speeches/nope/subtitles.vtt").status_code == 404


def test_track_is_withheld_when_the_transcript_has_changed(client, monkeypatch):
    # Offsets into a re-cleaned transcript are not stale but wrong — they would
    # caption one sentence with another. No subtitles is the safe answer.
    _corpus(monkeypatch, speech=_speech(text="Otro texto distinto por completo."),
            alignments=[_alignment()])

    assert client.get("/speeches/sp1/subtitles.vtt").status_code == 404


def test_subtitles_route_does_not_shadow_the_speech_itself(client, monkeypatch):
    _corpus(monkeypatch, alignments=[_alignment()])

    assert client.get("/speeches/sp1").json()["id"] == "sp1"


# ---- choosing the language ---------------------------------------------------------

def test_each_language_serves_its_own_track(client, monkeypatch):
    _corpus(monkeypatch, speech=_bilingual(), alignments=[
        _alignment(text=GALEGO, lang="gl"),
        _alignment(text=TEXT, lang="es", block_index=1, original=False)])

    galician = client.get("/speeches/sp1/subtitles.vtt?lang=gl")
    spanish = client.get("/speeches/sp1/subtitles.vtt?lang=es")

    assert "Grazas, presidente." in galician.text
    assert "Muchas gracias, presidente." in spanish.text


BASQUE_MIX = "Buenas tardes. Eskerrik asko, presidenta. Hemen gaude gaur."
RENDERED_MIX = "Buenas tardes. Muchas gracias, presidenta. Hoy estamos aquí."


def _two_spanish_blocks():
    """A speech given mostly in Spanish whose co-official passage the Diario also
    printed in Spanish: both blocks are ``es``, and only the role separates them."""
    return _speech(blocks=[
        {"lang": "es", "text": BASQUE_MIX, "original": True, "langs": ["es", "eu"]},
        {"lang": "es", "text": RENDERED_MIX, "original": False, "langs": ["es"]},
    ])


def test_two_spanish_blocks_serve_two_different_tracks(client, monkeypatch):
    """The language cannot tell these apart, so the role does. Without it the second
    track would answer for the first and the page would caption a speech with its own
    translation."""
    _corpus(monkeypatch, speech=_two_spanish_blocks(), alignments=[
        _alignment(text=BASQUE_MIX, lang="es"),
        _alignment(text=RENDERED_MIX, lang="es", block_index=1, original=False)])

    delivered = client.get("/speeches/sp1/subtitles.vtt?lang=es&original=true")
    rendered = client.get("/speeches/sp1/subtitles.vtt?lang=es&original=false")

    # Sliced at the fixture's cue offsets, so each is checked on the words that fall
    # inside a cue rather than on the whole sentence.
    assert "Eskerrik" in delivered.text and "Hemen gaude" in delivered.text
    assert "Muchas graci" in rendered.text and "Eskerrik" not in rendered.text


def test_two_spanish_blocks_are_both_advertised(client, monkeypatch):
    _corpus(monkeypatch, speech=_two_spanish_blocks(), alignments=[
        _alignment(text=BASQUE_MIX, lang="es"),
        _alignment(text=RENDERED_MIX, lang="es", block_index=1, original=False)])

    tracks = client.get("/speeches/sp1").json()["subtitles"]

    assert [(t["lang"], t["original"]) for t in tracks] == [("es", True), ("es", False)]


def test_asking_without_a_role_serves_the_block_the_language_names(client, monkeypatch):
    """A client that predates the flag asks ``?lang=es`` and must keep getting what it
    always got — on a co-official speech that is the TRANSLATION, since the Spanish
    block is the one being asked for."""
    _corpus(monkeypatch, speech=_bilingual(), alignments=[
        _alignment(text=GALEGO, lang="gl"),
        _alignment(text=TEXT, lang="es", block_index=1, original=False)])

    response = client.get("/speeches/sp1/subtitles.vtt?lang=es")

    assert response.status_code == 200
    assert "Muchas gracias, presidente." in response.text


def test_no_language_serves_the_as_delivered_track(client, monkeypatch):
    """What keeps a client that predates the second track working: it asks the way it
    always did and gets the language the speech was given in."""
    _corpus(monkeypatch, speech=_bilingual(), alignments=[
        _alignment(text=GALEGO, lang="gl"),
        _alignment(text=TEXT, lang="es", block_index=1, original=False)])

    response = client.get("/speeches/sp1/subtitles.vtt")

    assert "Grazas, presidente." in response.text


def test_a_language_the_speech_has_no_track_for_is_404(client, monkeypatch):
    _corpus(monkeypatch, alignments=[_alignment()])

    assert client.get("/speeches/sp1/subtitles.vtt?lang=eu").status_code == 404


def test_a_malformed_language_is_rejected(client, monkeypatch):
    # Nothing we could have issued, and it never reaches a collection lookup.
    # 400 rather than FastAPI's 422: the app maps validation errors itself.
    _corpus(monkeypatch, alignments=[_alignment()])

    assert client.get("/speeches/sp1/subtitles.vtt?lang=../etc").status_code == 400


# ---- the detail payload's indicator ------------------------------------------------

def test_detail_lists_the_track_and_its_language(client, monkeypatch):
    _corpus(monkeypatch, speech=_speech(text=GALEGO, lang="gl"),
            alignments=[_alignment(text=GALEGO, lang="gl")])

    assert client.get("/speeches/sp1").json()["subtitles"] == [
        {"lang": "gl", "original": True}]


def test_detail_lists_both_tracks_of_a_co_official_speech(client, monkeypatch):
    """And says which is the translation, so the page can label it rather than
    presenting a derived track as if it were the words spoken."""
    _corpus(monkeypatch, speech=_bilingual(), alignments=[
        _alignment(text=GALEGO, lang="gl"),
        _alignment(text=TEXT, lang="es", block_index=1, original=False)])

    assert client.get("/speeches/sp1").json()["subtitles"] == [
        {"lang": "gl", "original": True},
        {"lang": "es", "original": False},
    ]


def test_detail_reports_no_tracks_when_there_are_none(client, monkeypatch):
    _corpus(monkeypatch)

    assert client.get("/speeches/sp1").json()["subtitles"] == []


def test_detail_omits_a_track_it_would_refuse_to_serve(client, monkeypatch):
    # The page must never advertise a track that 404s on request.
    _corpus(monkeypatch, speech=_speech(text="Otro texto distinto por completo."),
            alignments=[_alignment()])

    assert client.get("/speeches/sp1").json()["subtitles"] == []


def test_a_stale_track_does_not_hide_its_healthy_sibling(client, monkeypatch):
    """One block re-cleaned since it was aligned must cost only its own track."""
    _corpus(monkeypatch, speech=_bilingual(original="Outro texto por completo."),
            alignments=[
                _alignment(text=GALEGO, lang="gl"),
                _alignment(text=TEXT, lang="es", block_index=1, original=False)])

    assert client.get("/speeches/sp1").json()["subtitles"] == [
        {"lang": "es", "original": False}]
