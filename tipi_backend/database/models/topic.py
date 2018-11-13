from tipi_backend.database import db


class Tag(db.EmbeddedDocument):
    tag = db.StringField()
    subtopic = db.StringField()
    regex = db.StringField()
    shuffle = db.BooleanField()


class Topic(db.Document):
    id = db.StringField(db_field='_id', primary_key=True)
    name = db.StringField()
    description = db.ListField(db.StringField())
    icon = db.StringField()
    tags = db.EmbeddedDocumentListField(Tag)

    meta = {'collection': 'topics'}
    # TODO Add indexes https://mongoengine-odm.readthedocs.io/guide/defining-documents.html#indexes
