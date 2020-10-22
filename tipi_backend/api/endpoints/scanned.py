import logging
import json

from flask import request, abort
from flask_restplus import Namespace, Resource, fields

from tipi_backend.api.business import save_scanned, get_scanned, search_scanned
from tipi_backend.api.endpoints import limiter
from tipi_backend.api.serializers import scanned_model


log = logging.getLogger(__name__)

ns = Namespace('scanned', description='Operations related to scanned documents')

@ns.route('/')
@ns.doc(False)
class ScannedCollection(Resource):
    decorators = [
        limiter.limit('10/hour', methods=['POST'])
    ]

    @ns.expect(scanned_model)
    @ns.response(201, 'Scanned successfully created.')
    def post(self):
        ''' Create a new scanned '''
        try:
            return save_scanned(ns.payload), 201
        except Exception as e:
            abort(500)

@ns.route('/<id>')
@ns.doc(False)
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Scanned not found.')
class ScannedItem(Resource):

    def get(self, id):
        """Returns details of a scanned document."""
        return get_scanned(id)

@ns.route('/search/<query>')
@ns.doc(False)
@ns.param(name='query', description='Search query', type=str, required=True, location=['path'])
@ns.response(404, 'Results not found.')
class SearchScanned(Resource):

    def get(self, query):
        """Returns list of verified scanned documents"""
        return search_scanned(query)
