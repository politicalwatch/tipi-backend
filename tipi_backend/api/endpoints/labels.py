import logging

from flask import request
from flask_restplus import Namespace, Resource
from werkzeug.contrib.cache import SimpleCache

from tipi_backend.api.parsers import parser_labels
from tipi_backend.api.business import extract_labels_from_text, get_tags


log = logging.getLogger(__name__)

ns = Namespace('labels', description='Operations related to label extraction')
cache = SimpleCache()

@ns.route('/extract')
@ns.expect(parser_labels)
class LabelsExtractor(Resource):
    def post(self):
        """Returns a dictionary of topics and tags matching the text."""
        cache_key = 'tags-for-labeling'
        tags = cache.get(cache_key)
        if tags is None:
            tags = get_tags()
            cache.set(cache_key, tags, timeout=5*60)

        return extract_labels_from_text(
            request.form['text'],
            tags
        )
