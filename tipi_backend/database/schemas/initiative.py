import marshmallow_mongoengine as ma
from tipi_backend.database.models.initiative import Initiative


class BasicField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return value


class InitiativeSchema(ma.ModelSchema):
    class Meta:
        model = Initiative
        model_fields_kwargs = {
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
