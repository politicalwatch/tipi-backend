from datetime import datetime
import json
import pcre

import tipi_alerts

from tipi_backend.database.models.topic import Topic
from tipi_backend.database.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_backend.database.models.deputy import Deputy
from tipi_backend.database.schemas.deputy import DeputySchema, DeputyExtendedSchema
from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.database.schemas.parliamentarygroup import ParliamentaryGroupSchema
from tipi_backend.database.models.initiative import Initiative
from tipi_backend.database.models.alert import Alert, Search
from tipi_backend.database.schemas.initiative import InitiativeSchema, InitiativeExtendedSchema
from tipi_backend.api.parsers import SearchInitiativeParser
from tipi_backend.api.managers.initiative_places import InitiativePlaceManager
from tipi_backend.api.managers.initiative_status import InitiativeStatusManager
from tipi_backend.api.managers.initiative_type import InitiativeTypeManager
from tipi_backend.database.models.stats import Stats
from tipi_backend.database.common import generateId


""" TOPICS METHODS """

def get_topics():
    return TopicSchema(many=True).dump(Topic.objects())

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
    return total, pages, parser.page, parser.per_page, InitiativeSchema(many=True).dump(Initiative.objects(__raw__=parser.params).limit(limit).skip(skip))

def get_initiative(id):
    return InitiativeExtendedSchema().dump(Initiative.objects.get(id=id))

def get_places():
    return InitiativePlaceManager().get_values()

def get_initiative_types():
    return InitiativeTypeManager().get_values()

def get_initiative_status():
    return InitiativeStatusManager().get_values()


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

def get_latest_initiatives(params):
    stats = json.loads(Stats.objects()[0].to_json())
    return _get_subdoc_stats(stats, 'latest', params['topic'], 'initiatives')

def get_places_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'placesBySubtopics', params['subtopic'], 'places')
    return _get_subdoc_stats(stats, 'placesByTopics', params['topic'], 'places')


""" LABEL EXTRACTOR METHODS """

def get_tags():
    return Topic.get_tags()

def extract_labels_from_text(text, tags):
    tags_found = []
    for line in text.splitlines():
        for tag in tags:
            if pcre.search(tag['compiletag'], line):
                tag_copy = tag.copy()
                tag_copy.pop('compiletag')
                if tag_copy not in tags_found:
                    tags_found.append(tag_copy)

    return {
        'topics': sorted(list(set([tag['topic'] for tag in tags_found]))),
        'tags': sorted([
            { 'topic': t['topic'], 'subtopic': t['subtopic'], 'tag': t['tag'] }
            for t in tags_found
            ], key=lambda t: t['topic'])
    }


""" ALERTS METHODS """

def save_alert(payload):
    alert = Alert.objects(email=payload['email']).first()
    if not alert:
        alert = Alert(
                id=generateId(payload['email']),
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
    tipi_alerts.init()
    tipi_alerts.validate.send_validation_emails.apply_async()

def _add_search_to_alert(search, alert):
    now = datetime.now()
    hash = generateId(alert.email, str(search), str(now))
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
