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
    return InitiativeSchema(many=True).dump(Initiative.objects(__raw__=parser.params)[parser.offset:(parser.offset+parser.limit)])

def get_initiative(id):
    return InitiativeExtendedSchema().dump(Initiative.objects.get(id=id))

def get_places():
    return get_unique_values(Initiative, 'place')

def get_initiative_types():
    # TODO Change by inmutable list of values
    return get_unique_values(Initiative, 'initiative_type_alt')

def get_initiative_states():
    return [
            'Aprobado',
            'Respondida',
            'Celebrada',
            'En tramitación',
            'Rechazada',
            'Retirada',
            'No admitida a trámite',
            'No debatida',
            'Convertida en otra',
            'Acumulada en otra',
            ]
