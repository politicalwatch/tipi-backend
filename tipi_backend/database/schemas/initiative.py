import marshmallow_mongoengine as ma
from tipi_backend.database.models.initiative import Initiative


class AuthorsField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return obj.author_others + obj.author_parliamentarygroups 

class DeputiesField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return value


class InitiativeSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
        model_skip_values = [None]
        model_fields_kwargs = {
                'author_deputies': {'load_only': True},
                'author_parliamentarygroups': {'load_only': True},
                'author_others': {'load_only': True},
                'created': {'load_only': True},
                'place': {'load_only': True},
                'processing': {'load_only': True},
                'url': {'load_only': True},
                'tags': {'load_only': True},
                'tagged': {'load_only': True},
                }

    authors = AuthorsField(attribute='author_parliamentarygroups')
    deputies = DeputiesField(attribute='author_deputies')


class InitiativeExtendedSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
        model_skip_values = [None]
        model_fields_kwargs = {
                'author_deputies': {'load_only': True},
                'author_parliamentarygroups': {'load_only': True},
                'author_others': {'load_only': True},
                'tagged': {'load_only': True},
                }

    authors = AuthorsField(attribute='author_parliamentarygroups')
    deputies = DeputiesField(attribute='author_deputies')
    related = ma.fields.Method(serialize="_related_serializer")

    def _related_serializer(self, obj):
        related = InitiativeSchema(many=True).dump(Initiative.all(reference=obj['reference']))
        if related.errors:
            return []
        related = [r for r in related.data if r['id'] != obj['id']]
        self._process_soft_related(related)
        return related

    # Soft related means that it is related but des not have any topics
    def _process_soft_related(self, related):
        for r in related:
            if len(r['topics']) is 0:
                del r['id']
