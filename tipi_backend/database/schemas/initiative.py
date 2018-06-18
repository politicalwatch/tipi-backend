import marshmallow_mongoengine as ma
from tipi_backend.database.models.initiative import Initiative


class AuthorsField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return obj.author_parliamentarygroups + obj.author_others

class DeputiesField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return value


class InitiativeSchema(ma.ModelSchema):
    authors = AuthorsField(attribute='author_parliamentarygroups')
    deputies = DeputiesField(attribute='author_deputies')
    class Meta:
        model = Initiative
        model_skip_values = [None]
        model_fields_kwargs = {
                'author_deputies': {'load_only': True},
                'author_parliamentarygroups': {'load_only': True},
                'author_others': {'load_only': True},
                'created': {'load_only': True},
                'reference': {'load_only': True},
                'initiative_type': {'load_only': True},
                'initiative_type_alt': {'load_only': True},
                'place': {'load_only': True},
                'processing': {'load_only': True},
                'url': {'load_only': True},
                'tags': {'load_only': True},
                'tagged': {'load_only': True},
                }


class InitiativeExtendedSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
