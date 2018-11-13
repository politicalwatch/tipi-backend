from tipi_backend.database import db


class ParliamentaryGroup(db.Document):
    id = db.StringField(db_field='_id', primary_key=True)
    name = db.StringField()
    shortname = db.StringField()
    active = db.BooleanField()

    meta = {
            'collection': 'parliamentarygroups',
            'ordering': ['name'],
            'indexes': ['name']
            }
