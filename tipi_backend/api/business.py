from datetime import date, datetime
import json
import logging
import time
from functools import lru_cache
from importlib import import_module as im

from natsort import natsorted, ns

import tipi_tasks

from tipi_data import DoesNotExist
from tipi_data.models.alert import Alert, Search
from tipi_data.models.scanned import Scanned as ScannedModel
from tipi_data.repositories.alerts import Alerts
from tipi_data.repositories.deputies import Deputies
from tipi_data.repositories.initiatives import Initiatives
from tipi_data.repositories.initiativetypes import InitiativeTypes
from tipi_data.repositories.knowledgebases import KnowledgeBases
from tipi_data.repositories.parliamentarygroups import ParliamentaryGroups
from tipi_data.repositories.places import Places
from tipi_data.repositories.scanned import Scanned
from tipi_data.repositories.sessions import Sessions
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
)
from tipi_data.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_data.utils import generate_id

from tipi_backend.settings import Config
from tipi_backend.api.parsers import SearchInitiativeParser, InitiativeParser

log = logging.getLogger(__name__)


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


def get_speech(id):
    """An all-digits id is the Congress intervention id (``video_id``) — the
    public, stable identifier once the sitting's video is published; anything
    else is the internal ``_id`` (which also covers the pre-video window)."""
    if id.isdigit():
        try:
            return SpeechExtendedSchema.model_validate(Speeches.get_by_video_id(id))
        except DoesNotExist:
            pass
    return SpeechExtendedSchema.model_validate(Speeches.get(id))


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


def semantic_search_speeches(params):
    """Natural-language grouped search: ``per_page`` distinct speeches (Qdrant
    groups passages by speech_id), hydrated from Mongo into the same compact
    card as the browse list. Requests one extra group as a ``has_more`` probe."""
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
    for group in groups:  # keep Qdrant relevance order, not Mongo's date sort
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
        "semantic_query": result.semantic_query,
        "filters": resolution.filters,
        "notes": resolution.notes,
        "unresolved": [
            {
                "field": entity.field,
                "value": entity.value,
                "blocking": entity.blocking,
                "suggestion": entity.suggestion,
            }
            for entity in resolution.unresolved
        ],
    }
    return meta, results


def get_places():
    return [PlaceSchema.model_validate(p) for p in Places.get_all()]


def get_initiative_types():
    return [InitiativeTypeSchema.model_validate(it) for it in InitiativeTypes.get_all()]


def get_initiative_status():
    ism = im("tipi_backend.api.managers.{}.initiative_status".format(Config.COUNTRY))
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


def search_verified_scanned(query):
    documents = Scanned.search_verified(query)

    return [ScannedSchema.model_validate(d) for d in documents]
