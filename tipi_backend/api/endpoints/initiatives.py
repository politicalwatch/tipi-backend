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
# Initiative parameters
@ns.param(name='topic', description='Topic', type=str, default='', location=['query'], help='Invalid topic')
@ns.param(name='tags', description='Tags', type=str, default='', location=['query'], help='Invalid tags')
@ns.param(name='author', description='Author', type=str, default='', location=['query'], help='Invalid author')
# TODO: Poner las fechas como datetime (adaptar la funcion fecha)
# def email(email_str):
#     if valid_email(email_str):
#         return email_str
#     else:
#         raise ValueError('{} is not a valid email'.format(email_str))
@ns.param(name='startdate', description='Start date', type=str, location=['query'], help='Invalid start date')
@ns.param(name='enddate', description='Start date', type=str, location=['query'], help='Invalid end date')
@ns.param(name='place', description='Place', type=str, default='', location=['query'], help='Invalid place')
@ns.param(name='reference', description='Reference', type=str, default='', location=['query'], help='Invalid reference')
@ns.param(name='type', description='Type', type=str, default='', location=['query'], help='Invalid type')
# TODO: Terminar de completar los estados
@ns.param(name='state', description='State', type=str, default='', choices=('Aprobada', 'Rechazada'), location=['query'], help='Invalid state')
@ns.param(name='title', description='Title', type=str, default='', location=['query'], help='Invalid title')
# Common parameters
@ns.param('limit', 'Limit', type=int, default=20, location=['query'], help='Invalid limit')
@ns.param('offset', 'Offset', type=int, default=0, location=['query'], help='Invalid offset')
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
