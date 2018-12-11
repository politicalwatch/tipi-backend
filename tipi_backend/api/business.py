import itertools
import json
import pcre

from tipi_backend.database.models.topic import Topic
from tipi_backend.database.schemas.topic import TopicSchema, TopicExtendedSchema
from tipi_backend.database.models.deputy import Deputy
from tipi_backend.database.schemas.deputy import DeputySchema, DeputyExtendedSchema
from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.database.schemas.parliamentarygroup import ParliamentaryGroupSchema
from tipi_backend.database.models.initiative import Initiative
from tipi_backend.database.schemas.initiative import InitiativeSchema, InitiativeExtendedSchema
from tipi_backend.api.parsers import SearchInitiativeParser
from tipi_backend.api.managers.initiative_places import InitiativePlaceManager
from tipi_backend.api.managers.initiative_status import InitiativeStatusManager
from tipi_backend.api.managers.initiative_type import InitiativeTypeManager
from tipi_backend.database.models.stats import Stats


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
    tags = []
    delimiter = '.*'
    for topic in Topic.objects():
        for tag in topic['tags']:
            if tag['shuffle']:
                for permutation in itertools.permutations(tag['regex'].split(delimiter)):
                    tags.append({
                        'topic': topic['name'],
                        'compiletag': pcre.compile('(?i)' + delimiter.join(permutation)),
                        'tag': tag['tag'],
                        'subtopic': tag['subtopic'],
                    })
            else:
                tags.append({
                    'topic': topic['name'],
                    'compiletag': pcre.compile('(?i)' + tag['regex']),
                    'tag': tag['tag'],
                    'subtopic': tag['subtopic']
                })
    return tags


def extract_labels_from_text(text, tags):
    tags_found = []
    for tag in tags:
        if pcre.search(tag['compiletag'], text):
            tags_found.append(tag)

    return {
        'topics': list(set([tag['topic'] for tag in tags_found])),
        'tags': [{ 'topic': t['topic'], 'subtopic': t['subtopic'], 'tag': t['tag'] } for t in tags_found]
    }
