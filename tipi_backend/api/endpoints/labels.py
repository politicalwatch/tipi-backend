import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.business import extract_labels_from_text, get_tags

log = logging.getLogger(__name__)

ns = api.namespace('labels', description='Operations related to label extraction')


@ns.route('/extract')
@ns.param(name='text', description='Text to be parsed for tags', type=str, required=True, location='form', help='Invalid identifier')
class LabelsExtractor(Resource):
    def post(self):
        """Returns a dictionary of topics and tags matching the text."""
        return extract_labels_from_text(
            request.form['text'],
            get_tags()
        )