from tipi_backend.database import db


class Search(db.DynamicEmbeddedDocument):
    hash = db.StringField()
    search = db.StringField()
    dbsearch = db.StringField()
    created = db.DateTimeField()
    validated = db.BooleanField(default=False)

class Alert(db.Document):
    id = db.StringField(db_field='_id', primary_key=True)
    email = db.EmailField()
    searches = db.EmbeddedDocumentListField(Search)

    meta = {'collection': 'alerts'}
    # TODO Add indexes https://mongoengine-odm.readthedocs.io/guide/defining-documents.html#indexes
