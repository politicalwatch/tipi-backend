import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.business import extract_labels_from_text, get_tags
from werkzeug.contrib.cache import SimpleCache


log = logging.getLogger(__name__)

ns = api.namespace('labels', description='Operations related to label extraction')
cache = SimpleCache()


@ns.route('/extract')
@ns.param(name='text', description='Text to be parsed for tags', type=str, required=True, location='form', help='Invalid identifier')
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