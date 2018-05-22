import marshmallow_mongoengine as ma
from tipi_backend.database.models.initiative import Initiative


class BasicField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return value


class InitiativeSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
        model_fields_kwargs = {
                'topics': {'load_only': True},
                'tags': {'load_only': True},
                'tagged': {'load_only': True},
                }


class InitiativeExtendedSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
