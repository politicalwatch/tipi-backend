""" TOPICS METHODS """

from tipi_backend.database.models.topic import Topic
from tipi_backend.database.schemas.topic import TopicSchema, TopicExtendedSchema

def get_topics():
    return TopicSchema(many=True).dump(Topic.objects())

def get_topic(id):
    return TopicExtendedSchema().dump(Topic.objects.get(id=id))



""" DEPUTIES METHODS """

from tipi_backend.database.models.deputy import Deputy
from tipi_backend.database.schemas.deputy import DeputySchema, DeputyExtendedSchema

def get_deputies():
    return DeputySchema(many=True).dump(Deputy.objects(active=True))

def get_deputy(id):
    return DeputyExtendedSchema().dump(Deputy.objects.get(id=id))



""" PARLIAMENTARY GROUPS METHODS """

from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup
from tipi_backend.database.schemas.parliamentarygroup import ParliamentaryGroupSchema

def get_parliamentarygroups():
    return ParliamentaryGroupSchema(many=True).dump(ParliamentaryGroup.objects(active=True))

def get_parliamentarygroup(id):
    return ParliamentaryGroupSchema().dump(ParliamentaryGroup.objects.get(id=id))



""" INITIATIVES METHODS """

from tipi_backend.database.models.initiative import Initiative
from tipi_backend.database.schemas.initiative import InitiativeExtendedSchema

def search_initiatives():
    # TODO
    return "List of initiatives"

def get_initiative(id):
    return InitiativeExtendedSchema().dump(Initiative.objects.get(id=id))
