from tipi_backend.database import db


class Stats(db.DynamicDocument):
    meta = {'collection': 'statistics'}
