import logging
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from tipi_backend.api.business import search_speeches, get_speech, speech_subtitles
from tipi_backend.api.request_models import SpeechesQuery
from tipi_backend.api.serialization import serialize


log = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.get("/")
def list_speeches(query: Annotated[SpeechesQuery, Query()]):
    """Returns a paginated list of speeches (compact, without text).

    Filter by ``session`` (a sitting id — returned in delivery order), ``reference``
    (an initiative — the debate view is ``session`` + ``reference``), ``speaker``,
    ``group``, ``legislature``, ``mention`` (a person id named in the speech) and a
    ``startdate``/``enddate`` range."""
    total, pages, page, per_page, speeches = search_speeches(query.model_dump())
    return {
        "query_meta": {
            "total": total,
            "pages": pages,
            "page": page,
            "per_page": per_page,
        },
        "speeches": serialize(speeches),
    }


# A player caches its subtitle track for as long as it holds the page, and cues only
# change when a speech is re-aligned — rare, and never urgent. An hour keeps repeat
# views off the database without making a correction wait for a deploy.
_SUBTITLES_CACHE = "public, max-age=3600"


@router.get("/{id}/subtitles.vtt")
def get_speech_subtitles(
    id: str,
    lang: Annotated[str | None, Query(
        min_length=2, max_length=8, pattern=r"^[A-Za-z-]+$",
        description="Which language's track. Omitted means the as-delivered one, "
                    "which is the only track a monolingual speech has.")] = None,
    original: Annotated[bool | None, Query(
        description="Which of two blocks of the SAME language is wanted: the one that "
                    "was delivered, or the Diario's rendering of a passage of it. "
                    "Omitted means the as-delivered one.")] = None,
):
    """The WebVTT subtitle track of one speech, for a player's ``<track>``.

    The cues are timed against the intervention's own video by forced alignment of
    the Diario de Sesiones transcript, so the words are the stenographers' and only
    the timing is a model's. Rendered per request from the stored cue offsets, never
    from a file: subtitles are a projection of the transcript and cannot drift from
    it. 404 covers every way there can be no track — unknown speech, never aligned,
    no track in the language asked for, or aligned against a transcript that has since
    changed — because a player treats them all the same way.

    A co-official-language intervention has two tracks, the language it was delivered
    in and Spanish, which is why the language is a parameter. It is optional so a
    client that predates the second track keeps working unchanged; HTTP caches key on
    the query string, so the two tracks cache independently without extra headers.

    The language does not always separate them: a speech given mostly in Spanish, one
    passage of which the Diario also printed in Spanish, has two Spanish blocks and
    they differ only in what they are — hence ``original``, which is likewise optional
    and likewise defaults to what was said.

    Two path segments after ``/speeches`` so it never shadows ``/speeches/{id}``.
    """
    try:
        track = speech_subtitles(id, lang, original)
    except Exception as e:
        log.error(e)
        track = None
    if track is None:
        return JSONResponse(status_code=404, content={"Error": "No subtitles found"})
    return PlainTextResponse(
        track, media_type="text/vtt; charset=utf-8",
        headers={"Cache-Control": _SUBTITLES_CACHE})


@router.get("/{id}")
def get_speech_item(id: str):
    """Returns a speech in full, including its per-language text blocks and mentions.

    ``id`` accepts the Congress intervention id (``video_id``, all digits) or the
    internal speech id."""
    try:
        return serialize(get_speech(id))
    except Exception as e:
        log.error(e)
        return JSONResponse(status_code=404, content={"Error": "No speech found"})
