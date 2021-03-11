from datetime import datetime
from os import environ as env
import json
import ast
import pcre
import logging
import time
import re
from importlib import import_module as im

import tipi_tasks

from tipi_data.models.topic import Topic
from tipi_data.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_data.models.deputy import Deputy
from tipi_data.schemas.deputy import DeputySchema, DeputyExtendedSchema
from tipi_data.models.parliamentarygroup import ParliamentaryGroup
from tipi_data.schemas.parliamentarygroup import ParliamentaryGroupSchema
from tipi_data.models.initiative import Initiative
from tipi_data.models.initiative_type import InitiativeType
from tipi_data.models.alert import Alert, Search
from tipi_data.schemas.initiative import InitiativeSchema, InitiativeExtendedSchema
from tipi_data.schemas.initiative_type import InitiativeTypeSchema
from tipi_data.models.place import Place
from tipi_data.schemas.place import PlaceSchema
from tipi_data.models.stats import Stats
from tipi_data.models.scanned import Scanned
from tipi_data.schemas.scanned import ScannedSchema
from tipi_data.utils import generate_id

from tipi_backend.settings import Config
from tipi_backend.api.parsers import SearchInitiativeParser, InitiativeParser


""" TOPICS METHODS """

def get_topics():
    return TopicSchema(many=True).dump(Topic.objects.natsorted())

def get_topic(id):
    return TopicExtendedSchema().dump(Topic.objects.get(id=id))


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
    return total, pages, parser.page, parser.per_page, serializer(many=True).dump(Initiative.objects(__raw__=parser.params).limit(limit).skip(skip))

def get_initiative(id, params):
    parser = InitiativeParser(params)
    serializer = parser.serializer
    return serializer().dump(Initiative.objects.get(id=id))

def get_places():
    return PlaceSchema(many=True).dump(Place.objects())

def get_initiative_types():
    return InitiativeTypeSchema(many=True).dump(InitiativeType.objects())

def get_initiative_status():
    ism = im('tipi_backend.api.managers.{}.initiative_status'.format(Config.COUNTRY))
    return ism.InitiativeStatusManager().get_values()


""" STATS METHODS """

def get_overall_stats():
    return json.loads(Stats.objects()[0].to_json())['overall']

def _get_subdoc_stats(stats, key, value, returnkey):
    subdoc_stats = [x for x in stats[key] if x['_id'] == value]
    if len(subdoc_stats) == 0:
        return {}
    return subdoc_stats[0][returnkey]

def get_deputies_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'deputiesBySubtopics', params['subtopic'], 'deputies')
    return _get_subdoc_stats(stats, 'deputiesByTopics', params['topic'], 'deputies')

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


""" TAGGER METHODS """

def get_tags():
    return Topic.get_tags()


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
