from tipi_backend.database import db
from tipi_backend.database.models.initiative import Tag


class ScannedResult(db.DynamicEmbeddedDocument):
    topics = db.ListField(db.StringField(), default=list)
    tags = db.EmbeddedDocumentListField(Tag, default=list)

class Scanned(db.Document):
    id = db.StringField(db_field='_id', primary_key=True)
    title = db.StringField()
    extract = db.StringField()
    result = db.EmbeddedDocumentField(ScannedResult)
    created = db.DateTimeField()

    meta = {'collection': 'scanned'}
    # TODO Add indexes https://mongoengine-odm.readthedocs.io/guide/defining-documents.html#indexes
