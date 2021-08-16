from datetime import datetime
from os import environ as env
import json
import ast
import logging
import time
import re
from importlib import import_module as im

from natsort import natsorted, ns

import tipi_tasks

from tipi_data.models.alert import Alert, Search
from tipi_data.models.deputy import Deputy
from tipi_data.models.initiative import Initiative
from tipi_data.models.initiative_type import InitiativeType
from tipi_data.models.parliamentarygroup import ParliamentaryGroup
from tipi_data.models.place import Place
from tipi_data.models.scanned import Scanned
from tipi_data.models.stats import Stats
from tipi_data.models.topic import Topic
from tipi_data.repositories.initiatives import Initiatives
from tipi_data.repositories.knowledgebases import KnowledgeBases
from tipi_data.repositories.tags import Tags
from tipi_data.repositories.topics import Topics
from tipi_data.schemas.deputy import DeputySchema, DeputyExtendedSchema
from tipi_data.schemas.initiative import InitiativeSchema, InitiativeExtendedSchema
from tipi_data.schemas.initiative_type import InitiativeTypeSchema
from tipi_data.schemas.parliamentarygroup import ParliamentaryGroupSchema
from tipi_data.schemas.place import PlaceSchema
from tipi_data.schemas.scanned import ScannedSchema
from tipi_data.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_data.utils import generate_id

from tipi_backend.settings import Config
from tipi_backend.api.parsers import SearchInitiativeParser, InitiativeParser


""" TOPICS METHODS """

def get_topics(kb=False):
    if kb:
        return TopicSchema(many=True).dump(Topics.by_kb(kb))

    return TopicSchema(many=True).dump(Topics.get_public())

def get_topic(id):
    return TopicExtendedSchema().dump(Topics.get(id))


""" DEPUTIES METHODS """

def get_deputies(params):
    if params['name'] is None:
        del(params['name'])
    return DeputySchema(many=True).dump(Deputy.objects(__raw__=params))

def get_deputy(id):
    return DeputyExtendedSchema().dump(Deputy.objects.get(id=id))


""" PARLIAMENTARY GROUPS METHODS """

def get_parliamentarygroups(params):
    if params['name'] is None:
        del(params['name'])
    return ParliamentaryGroupSchema(many=True).dump(ParliamentaryGroup.objects(__raw__=params))

def get_parliamentarygroup(id):
    return ParliamentaryGroupSchema().dump(ParliamentaryGroup.objects.get(id=id))


""" INITIATIVES METHODS """

def search_initiatives(params):
    parser = SearchInitiativeParser(params)
    total = Initiative.objects(__raw__=parser.params).count()
    pages = int(total/parser.per_page) + 1 if parser.per_page > 0 else 1
    limit = None if parser.per_page == -1 else parser.per_page
    skip = None if limit is None else (parser.page-1)*limit
    serializer = parser.serializer

    kb = parser.kb
    return total, pages, parser.page, parser.per_page, serializer(kb=kb, many=True).dump(Initiatives.by_query(parser.params).limit(limit).skip(skip))

def get_initiative(id, params):
    parser = InitiativeParser(params)
    serializer = parser.serializer
    kb = parser.kb
    return serializer(kb=kb).dump(Initiatives.get(id))

def get_places():
    return PlaceSchema(many=True).dump(Place.objects())

def get_initiative_types():
    initiative_types = InitiativeType.objects()
    return InitiativeTypeSchema(many=True).dump(initiative_types)

def get_initiative_status():
    ism = im('tipi_backend.api.managers.{}.initiative_status'.format(Config.COUNTRY))
    return ism.InitiativeStatusManager().get_values()


""" STATS METHODS """

def get_overall_stats(params):
    kbs = get_kbs(params)
    all_kbs = KnowledgeBases.get_all()
    kbs_to_remove = list(set(all_kbs) - set(kbs))

    output = json.loads(Stats.objects()[0].to_json())['overall']

    for kb in kbs_to_remove:
        del output['topics'][kb]
        del output['subtopics'][kb]
        del output[kb]

    return output

def _get_subdoc_stats(stats, key, value, returnkey, kbs):
    result = {}
    for kb in kbs:
        subdoc_stats = [x for x in stats[key][kb] if x['_id'] == value]
        if len(subdoc_stats) != 0:
            result[kb] = subdoc_stats[0][returnkey]
    return result

def get_deputies_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    kb = get_kbs(params)
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'deputiesBySubtopics', params['subtopic'], 'deputies', kb)
    return _get_subdoc_stats(stats, 'deputiesByTopics', params['topic'], 'deputies', kb)

def get_parliamentarygroups_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'parliamentarygroupsBySubtopics', params['subtopic'], 'parliamentarygroups')
    return _get_subdoc_stats(stats, 'parliamentarygroupsByTopics', params['topic'], 'parliamentarygroups')

def get_places_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'placesBySubtopics', params['subtopic'], 'places')
    return _get_subdoc_stats(stats, 'placesByTopics', params['topic'], 'places')

def get_topics_by_parliamentarygroup_stats(params):
    try:
        ParliamentaryGroup.objects().get(name=params['parliamentarygroup'])
    except Exception:
        return [], 404
    stats = json.loads(Stats.objects[0].to_json())
    topics = []
    for topic_element in stats['parliamentarygroupsByTopics']:
        filtered_initiatives = [
                x['initiatives']
                for x in topic_element['parliamentarygroups']
                if x['_id'] == params['parliamentarygroup']
                ]
        topics.append({
            'topic': topic_element['_id'],
            'initiatives': 0 if not filtered_initiatives else filtered_initiatives[0]
            })
    return natsorted(
            topics,
            lambda x: x['topic'],
            alg=ns.IGNORECASE
            )


""" KNOWLEDGEBASE METHODS """

def get_kbs(args):
    if 'knowledgebase' in args and args['knowledgebase'] is not None:
        return args['knowledgebase'].split(',')
    return KnowledgeBases.get_public()


""" TAGGER METHODS """

def get_tags():
    return Tags.get_all()


""" ALERTS METHODS """

def save_alert(payload):
    alert = Alert.objects(email=payload['email']).first()
    if not alert:
        alert = Alert(
                id=generate_id(payload['email']),
                email=payload['email']
                )
        _add_search_to_alert(payload['search'], alert)
    else:
        searches = [s.search for s in alert.searches]
        search_exists = False
        for search in searches:
            if payload['search'] == search:
                search_exists = True
                break
        if search_exists:
            return
        _add_search_to_alert(payload['search'], alert)

    result = alert.save()
    if not result:
        raise Exception

    '''
    Add init() before validate() to ensure it always use the same
    celery instance, despite flask multithrading
    '''
    tipi_tasks.init()
    tipi_tasks.validate.send_validation_emails.apply_async()

def _add_search_to_alert(search, alert):
    now = datetime.now()
    hash = generate_id(alert.email, str(search), str(now))
    alert.searches.append(Search(
        hash=hash,
        search=search,
        dbsearch=str(
            SearchInitiativeParser(
                json.loads(search)
                ).params
            ),
        created=now
        )
    )


''' SCANNED METHODS '''

def get_scanned(id):
    return ScannedSchema().dump(Scanned.objects.get(id=id))

def save_scanned(payload):
    EXPIRATION_OPTIONS = {
        '1m': 1,
        '3m': 3,
        '1y': 12
    }
    ONE_MONTH_IN_SECONDS = 60 * 60 * 24 * 30

    expiration = time.mktime(datetime.now().timetuple()) + (ONE_MONTH_IN_SECONDS * EXPIRATION_OPTIONS.get(payload.get('expiration', '1m')))

    scanned = Scanned(
        id=generate_id(payload['title'], payload['excerpt'], str(datetime.now())),
        title=payload['title'],
        excerpt=payload['excerpt'],
        result=ast.literal_eval(payload['result']),
        created=datetime.now(),
        expiration=datetime.fromtimestamp(expiration),
        verified=payload['verified']
    )

    saved = scanned.save()
    if not saved:
        raise Exception
    return {
        'id': scanned.id,
        'title': scanned.title,
        'excerpt': scanned.excerpt,
        'expiration': str(scanned.expiration)
    }

def search_verified_scanned(query):
    documents = Scanned.objects.filter(title=re.compile(query, re.IGNORECASE), verified=True)

    return ScannedSchema(many=True).dump(documents)
