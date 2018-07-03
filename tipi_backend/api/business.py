import json

from tipi_backend.database.models.topic import Topic
from tipi_backend.database.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_backend.database.models.deputy import Deputy
from tipi_backend.database.schemas.deputy import DeputySchema, DeputyExtendedSchema
from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.database.schemas.parliamentarygroup import ParliamentaryGroupSchema
from tipi_backend.database.models.initiative import Initiative
from tipi_backend.database.schemas.initiative import InitiativeSchema, InitiativeExtendedSchema
from tipi_backend.api.parsers import SearchInitiativeParser
from tipi_backend.api.utils import get_unique_values
from tipi_backend.api.managers.initiative_status import InitiativeStatusManager
from tipi_backend.api.managers.initiative_type import InitiativeTypeManager
from tipi_backend.database.models.stats import Stats


""" TOPICS METHODS """

def get_topics():
    return TopicSchema(many=True).dump(Topic.objects())

def get_topic(id):
    return TopicExtendedSchema().dump(Topic.objects.get(id=id))


""" DEPUTIES METHODS """

def get_deputies():
    return DeputySchema(many=True).dump(Deputy.objects(active=True))

def get_deputy(id):
    return DeputyExtendedSchema().dump(Deputy.objects.get(id=id))


""" PARLIAMENTARY GROUPS METHODS """

def get_parliamentarygroups():
    return ParliamentaryGroupSchema(many=True).dump(ParliamentaryGroup.objects(active=True))

def get_parliamentarygroup(id):
    return ParliamentaryGroupSchema().dump(ParliamentaryGroup.objects.get(id=id))


""" INITIATIVES METHODS """

def search_initiatives(params):
    parser = SearchInitiativeParser(params)
    total = Initiative.objects(__raw__=parser.params).count()
    pages = int(total/parser.per_page) + 1
    return total, pages, parser.page, parser.per_page, InitiativeSchema(many=True).dump(Initiative.objects(__raw__=parser.params).limit(parser.per_page).skip((parser.page-1)*parser.per_page))

def get_initiative(id):
    return InitiativeExtendedSchema().dump(Initiative.objects.get(id=id))

def get_places():
    return get_unique_values(Initiative, 'place')

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

def get_places_stats(params):
    stats = json.loads(Stats.objects()[0].to_json())
    if params['subtopic'] is not None:
        return _get_subdoc_stats(stats, 'placesBySubtopics', params['subtopic'], 'places')
    return _get_subdoc_stats(stats, 'placesByTopics', params['topic'], 'places')
