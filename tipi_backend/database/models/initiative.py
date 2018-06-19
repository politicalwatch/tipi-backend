from mongoengine.queryset import queryset_manager

from tipi_backend.database import db


class Tag(db.EmbeddedDocument):
    topic = db.StringField()
    subtopic = db.StringField()
    tag = db.StringField()


class Initiative(db.DynamicDocument):
    id = db.StringField(db_field='_id', primary_key=True)
    title = db.StringField()
    reference = db.StringField()
    initiative_type = db.StringField()
    initiative_type_alt = db.StringField()
    author_deputies = db.ListField(db.StringField(), default=list)
    author_parliamentarygroups = db.ListField(db.StringField(), default=list)
    author_others = db.ListField(db.StringField(), default=list)
    place = db.StringField()
    created = db.DateTimeField()
    updated = db.DateTimeField()
    # ended = db.DateTimeField()
    processing = db.StringField()
    status = db.StringField()
    topics = db.ListField(db.StringField(), default=list)
    tags = db.EmbeddedDocumentListField(Tag, default=list)
    tagged = db.BooleanField()
    url = db.URLField()

    meta = {'collection': 'initiatives'}
    # TODO Add indexes https://mongoengine-odm.readthedocs.io/guide/defining-documents.html#indexes

    @queryset_manager
    def objects(doc_cls, queryset):
        return queryset.filter(topics__not__size=0).order_by('-updated')
