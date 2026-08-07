from datetime import date, datetime, timezone
import json
import logging
import time
import unicodedata
from functools import lru_cache
from importlib import import_module as im

from langsmith import traceable
from natsort import natsorted, ns

import tipi_tasks

# Imported eagerly, unlike the search service below: this module of qhld_ai is pure
# domain logic with no dependencies of its own, so it costs nothing to a deployment
# that excludes the search namespace.
from qhld_ai.domain.subtitles import aligned_text, subtitle_track

from tipi_data import DoesNotExist
from tipi_data.models.alert import Alert, Search
from tipi_data.models.scanned import Scanned as ScannedModel
from tipi_data.models.query_gap import AMBIGUOUS, UNRESOLVED, QueryGapEvent
from tipi_data.models.search_rating import SearchRating
from tipi_data.repositories.alerts import Alerts
from tipi_data.repositories.dataset_updates import DatasetUpdates
from tipi_data.repositories.deputies import Deputies
from tipi_data.repositories.initiatives import Initiatives
from tipi_data.repositories.initiativetypes import InitiativeTypes
from tipi_data.repositories.knowledgebases import KnowledgeBases
from tipi_data.repositories.parliamentarygroups import ParliamentaryGroups
from tipi_data.repositories.places import Places
from tipi_data.repositories.query_gaps import QueryGaps
from tipi_data.repositories.scanned import Scanned
from tipi_data.repositories.search_ratings import SearchRatings
from tipi_data.repositories.sessions import Sessions
from tipi_data.repositories.speech_alignments import SpeechAlignments
from tipi_data.repositories.speeches import Speeches
from tipi_data.repositories.stats import Stats
from tipi_data.repositories.tags import Tags
from tipi_data.repositories.topics import Topics
from tipi_data.repositories.footprints import Footprints
from tipi_data.repositories.votings import Votings
from tipi_data.schemas.deputy import (
    DeputySchema,
    DeputyExtendedSchema,
    DeputyCompactSchema,
)
from tipi_data.schemas.initiative_type import InitiativeTypeSchema
from tipi_data.schemas.parliamentarygroup import (
    ParliamentaryGroupSchema,
    ParliamentaryGroupCompactSchema,
)
from tipi_data.schemas.place import PlaceSchema
from tipi_data.schemas.voting import VotingSchema
from tipi_data.schemas.footprint import (
    FootprintByTopicSchema,
    FootprintByDeputySchema,
    FootprintByParliamentaryGroupSchema,
)
from tipi_data.schemas.scanned import ScannedSchema
from tipi_data.schemas.session import SessionSchema
from tipi_data.schemas.speech import (
    SpeechCompactSchema,
    SpeechExtendedSchema,
    SubtitleTrackOut,
)
from tipi_data.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_data.utils import generate_id

from tipi_backend.infrastructure.config.settings import get_settings
from tipi_backend.api.parsers import SearchInitiativeParser, InitiativeParser

log = logging.getLogger(__name__)


""" STATUS METHODS """


def _as_utc_iso(moment):
    """``tipi_data``'s client is deliberately not ``tz_aware``, so stored UTC
    datetimes come back naive. Say so explicitly rather than serving a timestamp
    with no zone. Whole seconds: this is a freshness date, not a measurement."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (moment.astimezone(timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


# Written by the last step of the extraction pipeline rather than by a dataset, so
# it says when a run *finished*. Anything that stops the pipeline leaves it behind.
EXTRACTION_KEY = "extraction"


def get_dataset_updates():
    """When the data was last updated, and when each dataset was last rewritten.

    ``last_updated`` is the end of the last complete extraction run. Until a run has
    recorded one it falls back to the newest dataset, which is all older engines
    write — that keeps environments where the pipeline does not run (dev) meaningful.

    Unreadable bookkeeping must not take the status endpoint down with it, so a
    failure here reports "unknown" instead of raising.
    """
    try:
        updates = DatasetUpdates.get_all()
    except Exception:
        log.exception("Cannot read when the data was last updated")
        return {"last_updated": None, "datasets": {}}

    moments = {dataset: moment for dataset, moment in updates.items() if moment}
    completed = moments.pop(EXTRACTION_KEY, None)
    last_updated = completed or max(moments.values(), default=None)
    return {
        "last_updated": _as_utc_iso(last_updated) if last_updated else None,
        "datasets": {dataset: _as_utc_iso(moment)
                     for dataset, moment in sorted(moments.items())},
    }


""" TOPICS METHODS """


def get_topics(kb=False):
    if kb:
        return [TopicSchema.model_validate(t) for t in Topics.by_kb_sorted(kb)]

    return [TopicSchema.model_validate(t) for t in Topics.get_public()]


def get_topic(id):
    return TopicExtendedSchema.model_validate(Topics.get(id))


""" DEPUTIES METHODS """


def get_deputies(params):
    if params["name"] is None:
        del params["name"]
    is_compact = params["compact"]
    del params["compact"]

    if is_compact:
        return [DeputyCompactSchema.model_validate(d) for d in Deputies.get_by_query(params)]
    return DeputySchema.from_docs(Deputies.get_by_query(params))


def get_deputy(id):
    return DeputyExtendedSchema.from_doc(Deputies.get(id))


def get_deputies_birthdays():
    return DeputySchema.from_docs(Deputies.get_birthdays())


""" PARLIAMENTARY GROUPS METHODS """


def get_parliamentarygroups(params):
    if params["name"] is None:
        del params["name"]
    is_compact = params["compact"]
    del params["compact"]

    if is_compact:
        return [
            ParliamentaryGroupCompactSchema.model_validate(g)
            for g in ParliamentaryGroups.get_by_query(params)
        ]
    return ParliamentaryGroupSchema.from_docs(ParliamentaryGroups.get_by_query(params))


def get_parliamentarygroup(id):
    return ParliamentaryGroupSchema.from_doc(ParliamentaryGroups.get(id))


""" INITIATIVES METHODS """


def search_initiatives(params):
    parser = SearchInitiativeParser(params)
    total = Initiatives.count_by_query(parser.params)
    pages = int(total // parser.per_page) if parser.per_page > 0 else 1
    if total % parser.per_page > 0:
        pages += 1
    limit = None if parser.per_page == -1 else parser.per_page
    skip = None if limit is None else (parser.page - 1) * limit
    serializer = parser.serializer

    kb = parser.kb
    return (
        total,
        pages,
        parser.page,
        parser.per_page,
        [
            serializer.from_doc(i, kb)
            for i in Initiatives.by_query_paginated(parser.params, limit, skip)
        ],
    )


def get_initiative(id, params):
    parser = InitiativeParser(params)
    serializer = parser.serializer
    kb = parser.kb
    return serializer.from_doc(Initiatives.get(id=id), kb)


def get_initiatives_sitemap():
    return [{"id": i.id, "updated": i.updated} for i in Initiatives.sitemap()]


""" SESSIONS & SPEECHES METHODS """


def _pagination(total, page, per_page):
    """Mirror ``search_initiatives`` paging math: page count + Mongo limit/skip
    (``per_page == -1`` means unpaginated)."""
    pages = int(total // per_page) if per_page > 0 else 1
    if per_page > 0 and total % per_page > 0:
        pages += 1
    limit = None if per_page == -1 else per_page
    skip = None if limit is None else (page - 1) * limit
    return pages, limit, skip


def _date_range(params):
    """A ``date`` range condition (YYYYMMDD int) from ``startdate``/``enddate``;
    tolerates ISO ``YYYY-MM-DD`` input. Empty when neither bound is given."""
    rng = {}
    if params.get("startdate"):
        rng["$gte"] = int(str(params["startdate"]).replace("-", ""))
    if params.get("enddate"):
        rng["$lte"] = int(str(params["enddate"]).replace("-", ""))
    return rng


def _build_sessions_query(params):
    query = {}
    for field in ("legislature", "code"):
        if params.get(field):
            query[field] = params[field]
    date = _date_range(params)
    if date:
        query["date"] = date
    return query


def _build_speeches_query(params):
    query = {}
    if params.get("session"):
        query["session_id"] = params["session"]
    if params.get("reference"):
        query["references"] = params["reference"]  # array-membership match
    if params.get("mention"):
        query["mentions.person_id"] = params["mention"]
    for field in ("speaker", "group", "legislature"):
        if params.get(field):
            query[field] = params[field]
    date = _date_range(params)
    if date:
        query["date"] = date
    return query


def search_sessions(params):
    query = _build_sessions_query(params)
    total = Sessions.count_by_query(query)
    pages, limit, skip = _pagination(total, params["page"], params["per_page"])
    sessions = [
        SessionSchema.from_doc(s)
        for s in Sessions.by_query_paginated(query, limit, skip)
    ]
    return total, pages, params["page"], params["per_page"], sessions


def get_session(id):
    session = Sessions.get(id)
    speeches_count = Speeches.count_by_query({"session_id": id})
    return SessionSchema.from_doc(session, speeches_count=speeches_count)


def search_speeches(params):
    query = _build_speeches_query(params)
    total = Speeches.count_by_query(query)
    pages, limit, skip = _pagination(total, params["page"], params["per_page"])
    speeches = [
        SpeechCompactSchema.model_validate(s)
        for s in Speeches.by_query_paginated(query, limit, skip)
    ]
    return total, pages, params["page"], params["per_page"], speeches


def _resolve_speech(id):
    """The speech an id names. An all-digits id is the Congress intervention id
    (``video_id``) — the public, stable identifier once the sitting's video is
    published; anything else is the internal ``_id`` (which also covers the
    pre-video window). Raises ``DoesNotExist`` for an unknown speech."""
    if id.isdigit():
        try:
            return Speeches.get_by_video_id(id)
        except DoesNotExist:
            pass
    return Speeches.get(id)


def get_speech(id):
    speech = _resolve_speech(id)
    out = SpeechExtendedSchema.model_validate(speech)
    out.subtitles = _subtitle_track_of(speech)
    return out


def _subtitle_track_of(speech):
    """The subtitle track a page may load for this speech, or ``None``.

    Read through the same drift guard the track itself is served through, so the
    page never advertises subtitles that would 404 on request: cues carry offsets
    rather than text, and offsets into a transcript that has since been re-cleaned
    would caption one sentence with another.
    """
    summary = SpeechAlignments.summary(speech.id)
    if summary is None:
        return None
    text = aligned_text(speech.speech, summary.get("block_index"),
                        summary.get("lang"), summary.get("text_sha256"),
                        summary.get("text_length"))
    if text is None:
        log.warning(f"{speech.id} has an alignment made against different text")
        return None
    return SubtitleTrackOut(lang=summary.get("lang"))


def speech_subtitles(id):
    """The WebVTT track of one speech, or ``None`` if it has no usable one.

    Rendered here rather than stored: the track is a projection of the stored cue
    numbers over the stored transcript, so a correction to the text reaches the
    subtitles with no re-alignment and the two can never disagree.
    """
    speech = _resolve_speech(id)
    try:
        alignment = SpeechAlignments.get(speech.id)
    except DoesNotExist:
        return None
    return subtitle_track(alignment, speech.speech)


""" SEMANTIC SEARCH METHODS """


@lru_cache(maxsize=1)
def _natural_search():
    """One env-configured qhld-ai service for the whole process: its clients are
    cheap to build, but the entity resolver warms from the corpus (Mongo + a
    Qdrant scan) on first use, so the instance must survive across requests.
    Imported lazily so deployments that exclude the search namespace never pay
    the qhld-ai (langchain et al.) import."""
    from qhld_ai.application.search.natural_search import NaturalSearchSpeeches

    return NaturalSearchSpeeches()


@lru_cache(maxsize=256)
def _parse_query(q, today_iso):
    """Memoized LLM parse: "show more" repeats the same query with a longer
    exclude list, and must not pay (nor re-run) the parse on every click."""
    return _natural_search().parser.parse(q, date.fromisoformat(today_iso))


# Which resolver fields are worth mining. ``mentions`` and ``speaker`` are people, the
# point of the exercise; ``entities`` is the theme vocabulary, and a miss there is the
# same kind of gap for nearly no extra work. The rest are dictionary lookups over closed
# vocabularies (group, constituency, lang) or a role phrase the parser invented, so a
# miss says more about the parse than about our data.
_MINED_FIELDS = ("mentions", "speaker", "entities")
_PERSON_FIELDS = ("mentions", "speaker")
# Tokens that survive person-name normalisation but name nobody, so they must not become
# keys of their own. Index-side this class is caught by a part-of-speech gate, which needs
# spaCy; the backend does not ship it, and for query text a short list covers it: what is
# left after the courtesy and role words are stripped is either a name or one of these.
# Person fields only — an entity key keeps its prepositions ("guerra de gaza").
_KEYLESS_TOKENS = frozenset({
    "de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "a", "al", "en", "que",
    "don", "dona", "doña",
})


def _gap_key(field, value):
    """The canonical form that groups sightings of one surface, or "" to skip it.

    Reuses the resolver's own normalisers so a key here means what it means in the search
    path, with one addition for people: ``normalize_span`` keeps accents (index-side it
    reads properly accented transcripts), while query text is typed by users who leave
    them out — without folding them, "Sánchez" and "sanchez" would be filed as two
    different people.
    """
    from qhld_ai.domain.entities import normalize_entity
    from qhld_ai.domain.mentions import normalize_span

    if field not in _PERSON_FIELDS:
        # Left exactly as ``normalize_entity`` produces it, which is the key the corpus
        # itself is stamped with ("guerra de gaza"). It has its own stoplist and returns
        # "" for junk, and pruning function words here would only break that parity.
        return normalize_entity(value)
    # Courtesy and role words go first ("el señor Rueda" → "rueda"), which also empties a
    # span that was ONLY a courtesy form ("Su Señoría").
    key = _strip_accents(normalize_span(value)).strip()
    tokens = [t for t in key.split() if t not in _KEYLESS_TOKENS]
    return " ".join(tokens) if tokens else ""


def _strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if not unicodedata.combining(c))


def _record_query_gaps(query, resolution, semantic_query):
    """Keep the people and themes this search could not identify.

    Free evidence for catalog curation: the resolver already reports what it could not
    resolve, and — since it learned to say so — what it resolved only by breaking a tie
    arbitrarily. Both used to be logged and discarded.

    Called from the grouped search ONLY. ``speech_passages`` re-resolves the same query to
    highlight a detail page, so recording there would count one person's single search
    several times over.

    Never raises: a search must not fail because bookkeeping did.
    """
    try:
        parser_model = _natural_search().settings.query_parser_llm_model
        events = []
        for entity in resolution.unresolved:
            if entity.field not in _MINED_FIELDS:
                continue
            key = _gap_key(entity.field, entity.value)
            if not key:
                continue
            events.append(QueryGapEvent(
                field=entity.field, key=key, outcome=UNRESOLVED, value=entity.value,
                blocking=entity.blocking, suggestion=entity.suggestion,
                query=query, semantic_query=semantic_query,
                filters=resolution.filters, parser_model=parser_model))
        for match in getattr(resolution, "ambiguous", []):
            if match.field not in _MINED_FIELDS:
                continue
            key = _gap_key(match.field, match.value)
            if not key:
                continue
            events.append(QueryGapEvent(
                field=match.field, key=key, outcome=AMBIGUOUS, value=match.value,
                chosen=match.chosen, tied=match.tied,
                query=query, semantic_query=semantic_query,
                filters=resolution.filters, parser_model=parser_model))
        for event in events:
            QueryGaps.record(event)
    except Exception:
        log.exception("Could not record the query gaps for %r", query)


@traceable(name="semantic_search_speeches", run_type="chain")
def semantic_search_speeches(params):
    """Natural-language grouped search: ``per_page`` distinct speeches (Qdrant
    groups passages by speech_id), hydrated from Mongo into the same compact
    card as the browse list. Requests one extra group as a ``has_more`` probe.

    The traceable decorator makes this the LangSmith root span for the request,
    so the memoized parse (which runs OUTSIDE ``execute`` and is skipped on
    "show more" cache hits) and the ``natural_search`` span land in one trace
    instead of two roots. Inert unless LANGSMITH_TRACING is set."""
    today = date.today()
    parsed = _parse_query(params["q"], today.isoformat())
    result = _natural_search().execute(
        params["q"],
        today,
        k=params["per_page"] + 1,
        grouped=True,
        highlights=params["highlights"],
        exclude=set(params["exclude"]) or None,
        parsed=parsed,
    )
    has_more = len(result.hits) > params["per_page"]
    groups = result.hits[: params["per_page"]]

    by_id = {}
    if groups:
        docs = Speeches.by_query_paginated(
            {"_id": {"$in": [group.speech_id for group in groups]}}
        )
        by_id = {doc.id: doc for doc in docs}
    results = []
    for group in groups:  # keep Qdrant's own order, not Mongo's date sort
        speech = by_id.get(group.speech_id)
        if speech is None:
            log.warning("Indexed speech %s missing from Mongo", group.speech_id)
            continue
        results.append(
            {
                "speech": SpeechCompactSchema.model_validate(speech),
                "score": group.score,
                "highlights": [hit.payload.get("text", "") for hit in group.highlights],
            }
        )

    resolution = result.resolution
    meta = {
        "q": params["q"],
        "per_page": params["per_page"],
        "count": len(results),
        "has_more": has_more,
        # The topic the parser extracted, empty when the query named only filters
        # — and then ``browse`` is set: these are the newest speeches matching the
        # filters, ordered by date, and their passages matched nothing (there was
        # nothing to match), so a client must not present them as matches.
        "semantic_query": result.semantic_query,
        "browse": result.browse,
        "filters": resolution.filters,
        "notes": resolution.notes,
        "unresolved": [
            {
                "field": entity.field,
                "value": entity.value,
                "blocking": entity.blocking,
                "suggestion": entity.suggestion,
                # Which way it failed. Null is "nobody answers to that name";
                # "filtered_out" is "recognised, then ruled out by the rest of the
                # query" — two things a client has to word differently.
                "reason": getattr(entity, "reason", None),
            }
            for entity in resolution.unresolved
        ],
        # Values several people answered to. Nothing failed — ``kept`` is what the search
        # actually filtered on — but when it holds more than one name the results belong
        # to all of them, so a client can offer to narrow instead of implying one person.
        "ambiguous": [
            {
                "field": match.field,
                "value": match.value,
                "chosen": match.chosen,
                "tied": match.tied,
                "kept": match.kept,
            }
            for match in getattr(resolution, "ambiguous", [])
        ],
        # How to say the filter values that are opaque outside the search package, as
        # ``{field: {value: label}}`` — today the person ids a mentions filter holds.
        # A client shows the label and still filters on the value.
        "labels": getattr(resolution, "labels", {}),
    }
    # After the response is assembled, so bookkeeping can never come between the user and
    # their results.
    _record_query_gaps(params["q"], resolution, result.semantic_query)
    return meta, results


def speech_passages(id, params):
    """Every relevance-floored passage of a single speech for a query, for the
    detail page (which highlights all matches, not just the few on a result
    card). The id is resolved to the canonical ``_id`` that keys the Qdrant
    chunks, and an unknown speech raises ``DoesNotExist``. The parse is the
    memoized one, so arriving here from a results page skips the LLM call."""
    today = date.today()
    speech = _resolve_speech(id)
    parsed = _parse_query(params["q"], today.isoformat())
    result = _natural_search().passages(params["q"], today, speech.id, parsed=parsed)
    return [hit.payload.get("text", "") for hit in result.hits]


def get_places():
    return [PlaceSchema.model_validate(p) for p in Places.get_all()]


def get_initiative_types():
    return [InitiativeTypeSchema.model_validate(it) for it in InitiativeTypes.get_all()]


def get_initiative_status():
    ism = im("tipi_backend.api.managers.{}.initiative_status".format(get_settings().country))
    return ism.InitiativeStatusManager().get_values()


""" VOTING METHODS """


def get_voting(reference):
    return [VotingSchema.model_validate(v) for v in Votings.get_by(reference)]


""" STATS METHODS """


def get_overall_stats(params):
    kbs = get_kbs(params)
    all_kbs = KnowledgeBases.get_all()
    kbs_to_remove = list(set(all_kbs) - set(kbs))

    output = Stats.get().model_dump(by_alias=True)["overall"]

    for kb in kbs_to_remove:
        del output["topics"][kb]
        del output["subtopics"][kb]
        del output[kb]

    return output


def get_lastdays_stats(params):
    output = Stats.get().model_dump(by_alias=True)["lastdays"]

    return output


def _get_subdoc_stats(stats, key, value, returnkey, kbs):
    result = {}
    for kb in kbs:
        subdoc_stats = [x for x in stats[key][kb] if x["_id"] == value]
        if len(subdoc_stats) != 0:
            result[kb] = subdoc_stats[0][returnkey]
    return result


def get_deputies_stats(params):
    stats = Stats.get().model_dump(by_alias=True)
    kb = get_kbs(params)
    if params["subtopic"] is not None:
        return _get_subdoc_stats(
            stats, "deputiesBySubtopics", params["subtopic"], "deputies", kb
        )
    return _get_subdoc_stats(stats, "deputiesByTopics", params["topic"], "deputies", kb)


def get_parliamentarygroups_stats(params):
    stats = Stats.get().model_dump(by_alias=True)
    kb = get_kbs(params)
    if params["subtopic"] is not None:
        return _get_subdoc_stats(
            stats,
            "parliamentarygroupsBySubtopics",
            params["subtopic"],
            "parliamentarygroups",
            kb,
        )
    return _get_subdoc_stats(
        stats, "parliamentarygroupsByTopics", params["topic"], "parliamentarygroups", kb
    )


def get_places_stats(params):
    stats = Stats.get().model_dump(by_alias=True)
    kb = get_kbs(params)
    if params["subtopic"] is not None:
        return _get_subdoc_stats(
            stats, "placesBySubtopics", params["subtopic"], "places", kb
        )
    return _get_subdoc_stats(stats, "placesByTopics", params["topic"], "places", kb)


def get_topics_by_parliamentarygroup_stats(params):
    try:
        ParliamentaryGroups.get_by_name(params["parliamentarygroup"])
    except Exception:
        return [], 404
    stats = Stats.get().model_dump(by_alias=True)
    kbs = get_kbs(params)
    topics = []
    for kb in stats["parliamentarygroupsByTopics"]:
        topic_elements = stats["parliamentarygroupsByTopics"][kb]
        if kb not in kbs:
            continue
        for topic_element in topic_elements:
            filtered_initiatives = [
                x["initiatives"]
                for x in topic_element["parliamentarygroups"]
                if x["_id"] == params["parliamentarygroup"]
            ]
            topics.append(
                {
                    "topic": topic_element["_id"],
                    "initiatives": (
                        0 if not filtered_initiatives else filtered_initiatives[0]
                    ),
                }
            )
    return natsorted(topics, lambda x: x["topic"], alg=ns.IGNORECASE)


def get_by_week_stats():
    stats = Stats.get().model_dump(by_alias=True)
    return stats["byWeek"]


def get_topics_by_week_stats(params):
    result = []
    stats = Stats.get().model_dump(by_alias=True)
    for kb in KnowledgeBases.get_public():
        if kb != params["knowledgebase"]:
            continue
        result = list(
            filter(lambda x: x["_id"] == params["topic"], stats["topicsByWeek"][kb])
        )
    if len(result) > 0:
        return result[0]["byWeek"]
    return result


""" KNOWLEDGEBASE METHODS """


def get_kbs(args):
    if "knowledgebase" in args and args["knowledgebase"] is not None:
        return args["knowledgebase"].split(",")
    return KnowledgeBases.get_public()


""" FOOTPRINT METHODS """


def get_footprint_by_topic(params):
    return FootprintByTopicSchema.model_validate(Footprints.get_by_topic(params["topic"]))


def get_footprint_range_by_all_topics():
    return list(Footprints.get_range_by_all_topics())


def get_footprint_by_deputy(params):
    return FootprintByDeputySchema.model_validate(Footprints.get_by_deputy(params["deputy"]))


def get_footprint_by_parliamentarygroup(params):
    return FootprintByParliamentaryGroupSchema.model_validate(
        Footprints.get_by_parliamentarygroup(params["parliamentarygroup"])
    )


""" TAGGER METHODS """


def get_tags():
    return Tags.get_all()


""" ALERTS METHODS """


def save_alert(payload):
    alert = Alerts.get_by_email(payload["email"])
    if not alert:
        alert = Alert(id=generate_id(payload["email"]), email=payload["email"])
        _add_search_to_alert(payload["search"], alert)
    else:
        searches = [s.search for s in alert.searches]
        search_exists = False
        for search in searches:
            if payload["search"] == search:
                search_exists = True
                break
        if search_exists:
            return
        _add_search_to_alert(payload["search"], alert)

    result = Alerts.save(alert)
    if not result:
        raise Exception

    """
    Add init() before validate() to ensure it always use the same
    celery instance, despite flask multithrading
    """
    tipi_tasks.init()
    tipi_tasks.validate.send_validation_emails.apply_async()


def _add_search_to_alert(search, alert):
    now = datetime.now()
    hash = generate_id(alert.email, str(search), str(now))
    alert.searches.append(
        Search(
            hash=hash,
            search=search,
            dbsearch=str(SearchInitiativeParser(json.loads(search)).params),
            created=now,
        )
    )


""" SCANNED METHODS """


def get_scanned(id):
    return ScannedSchema.model_validate(Scanned.get(id))


def save_scanned(payload):
    EXPIRATION_OPTIONS = {"1m": 1, "3m": 3, "1y": 12}
    ONE_MONTH_IN_SECONDS = 60 * 60 * 24 * 30

    expiration = time.mktime(datetime.now().timetuple()) + (
        ONE_MONTH_IN_SECONDS * EXPIRATION_OPTIONS.get(payload.get("expiration", "1m"))
    )

    scanned = ScannedModel(
        id=generate_id(payload["title"], payload["excerpt"], str(datetime.now())),
        title=payload["title"],
        excerpt=payload["excerpt"],
        created=datetime.now(),
        expiration=datetime.fromtimestamp(expiration),
        verified=payload["verified"],
    )

    result = payload["result"]
    serialized_result = json.loads(result)
    tags = serialized_result["tags"]
    for tag in tags:
        scanned.add_tag(
            tag["knowledgebase"],
            tag["topic"],
            tag["subtopic"],
            tag["tag"],
            tag["times"],
        )

    saved = Scanned.save(scanned)
    if not saved:
        raise Exception
    return {
        "id": scanned.id,
        "title": scanned.title,
        "excerpt": scanned.excerpt,
        "expiration": str(scanned.expiration),
    }


def save_search_rating(payload):
    """Store one rating of one speech search.

    Append-only, so unlike ``save_alert`` there is no lookup-then-merge: rating the
    same search twice keeps both answers, and reconciling them is left to whoever
    reads the collection.
    """
    result_ids = payload.get("result_ids") or []
    rating = SearchRating(
        rating=payload["rating"],
        query=payload["query"],
        query_meta=payload.get("query_meta") or {},
        reasons=payload.get("reasons") or [],
        comment=payload.get("comment"),
        result_ids=result_ids,
        # Derived, never taken from the request: a client-supplied count could only
        # ever disagree with the ids it sent alongside it.
        results_count=len(result_ids),
        corpus=payload.get("corpus"),
    )
    saved = SearchRatings.save(rating)
    if not saved.inserted_id:
        raise Exception


def search_verified_scanned(query):
    documents = Scanned.search_verified(query)

    return [ScannedSchema.model_validate(d) for d in documents]
