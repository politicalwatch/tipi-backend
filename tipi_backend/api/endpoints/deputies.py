import logging

from flask import request
from flask_restplus import Resource
from mongoengine.queryset import DoesNotExist
from tipi_backend.api.restplus import api
from tipi_backend.api.business import get_deputies, get_deputy
from tipi_backend.api.validators import validate_id_as_hash

log = logging.getLogger(__name__)

ns = api.namespace('deputies', description='Operations related to deputies')


@ns.route('/')
class DeputiesCollection(Resource):

    def get(self):
        """Returns list of active deputies."""
        return get_deputies()


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@api.response(404, 'Deputy not found.')
class DeputyItem(Resource):

    @validate_id_as_hash
    def get(self, id):
        """Returns details of a deputy."""
        return get_deputy(id)
