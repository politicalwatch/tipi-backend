import logging

from flask import request
from flask_restplus import Namespace, Resource
from werkzeug.contrib.cache import SimpleCache

from tipi_backend.api.parsers import parser_labels_from_text
from tipi_backend.api.business import extract_labels_from_text, get_tags


log = logging.getLogger(__name__)

ns = Namespace('labels', description='Operations related to label extraction')
cache = SimpleCache()

class LabelsExtractor(Resource):
    def load_tags(self):
        cache_key = 'tags-for-labeling'
        self.tags = cache.get(cache_key)
        if self.tags is None:
            self.tags = get_tags()
            cache.set(cache_key, self.tags, timeout=5*60)


@ns.route('/extract-from-text')
@ns.expect(parser_labels_from_text)
class LabelsExtractorFromText(LabelsExtractor):
    def post(self):
        """Returns a dictionary of topics and tags matching the text."""
        self.load_tags()
        return extract_labels_from_text(
            request.form['text'],
            self.tags
        )
