import marshmallow_mongoengine as ma
from tipi_backend.database.models.parliamentarygroup import ParliamentaryGroup


class ParliamentaryGroupSchema(ma.ModelSchema):
    class Meta:
        model = ParliamentaryGroup
        model_fields_kwargs = {
                'active': {'load_only': True}
                }
