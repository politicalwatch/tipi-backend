import logging
import json

from flask import request, abort
from flask_restplus import Namespace, Resource, fields

from tipi_backend.api.business import save_scanned, get_scanned
from tipi_backend.api.serializers import scanned_model
from tipi_backend.api.validators import validate_id_as_hash


log = logging.getLogger(__name__)

ns = Namespace('scanned', description='Operations related to scanned documents')

@ns.route('/')
@ns.doc(False)
class ScannedCollection(Resource):

    @ns.expect(scanned_model)
    @ns.response(201, 'Scanned successfully created.')
    def post(self):
        ''' Create a new scanned '''
        try:
            return save_scanned(ns.payload)
        except Exception as e:
            abort(500)

@ns.route('/<id>')
@ns.doc(False)
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Scanned not found.')
class ScannedItem(Resource):

    @validate_id_as_hash
    def get(self, id):
        """Returns details of a scanned document."""
        return get_scanned(id)
