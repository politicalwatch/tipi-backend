import marshmallow_mongoengine as ma
from tipi_backend.database.models.place import Place


class PlaceSchema(ma.ModelSchema):
    class Meta:
        model = Place
