from tipi_backend.database import db


class SearchesTracker(db.DynamicDocument):
    meta = {'collection': 'searches_tracker'}
