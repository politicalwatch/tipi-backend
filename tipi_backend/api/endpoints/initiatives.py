import logging

from flask import request
from flask_restplus import Resource
from mongoengine.queryset import DoesNotExist

from tipi_backend.api.restplus import api
from tipi_backend.api.business import search_initiatives, get_initiative
from tipi_backend.api.validators import validate_id_as_hash


log = logging.getLogger(__name__)

ns = api.namespace('initiatives', description='Operations related to initiatives')



@ns.route('/')
# Common parameters
@ns.param('offset', 'Offset', type=int, default=0, location=['query'], help='Invalid offset')
@ns.param('limit', 'Limit', type=int, default=20, location=['query'], help='Invalid limit')
# Initiative parameters
@ns.param(name='title', description='Title', type=str, default='', location=['query'], help='Invalid title')
@ns.param(name='state', description='State', type=str, default='', location=['query'], help='Invalid state')
@ns.param(name='type', description='Type', type=str, default='', location=['query'], help='Invalid type')
@ns.param(name='reference', description='Reference', type=str, default='', location=['query'], help='Invalid reference')
@ns.param(name='place', description='Place', type=str, default='', location=['query'], help='Invalid place')
@ns.param(name='enddate', description='End date (yyyy-mm-dd)', type=str, location=['query'], help='Invalid end date')
@ns.param(name='startdate', description='Start date (yyyy-mm-dd)', type=str, location=['query'], help='Invalid start date')
@ns.param(name='deputy', description='Deputy', type=str, default='', location=['query'], help='Invalid deputy')
@ns.param(name='author', description='Author ("Gobierno" or some of the parliamentary groups)', type=str, default='', location=['query'], help='Invalid author')
@ns.param(name='tag', description='Tags', type=str, default='', location=['query'], help='Invalid tags')
@ns.param(name='topic', description='Topic', type=str, default='', location=['query'], help='Invalid topic')
#validation functions

class InitiativesCollection(Resource):

    def get(self):
        """Returns list of initiatives."""
        return search_initiatives(request.args)


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@api.response(404, 'Initiative not found.')
class InitiativeItem(Resource):

    @validate_id_as_hash
    def get(self, id):
        """Returns details of an initiative."""
        return get_initiative(id)
