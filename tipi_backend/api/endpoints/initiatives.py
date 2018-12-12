import logging
import json

from flask import request
from flask_restplus import Resource
from mongoengine.queryset import DoesNotExist

from tipi_backend.api.restplus import api
from tipi_backend.api.parsers import parser_initiative
from tipi_backend.api.business import search_initiatives, get_initiative
from tipi_backend.api.validators import validate_id_as_hash
from tipi_backend.database.models.searches_tracker import SearchesTracker


log = logging.getLogger(__name__)

ns = api.namespace('initiatives', description='Operations related to initiatives')



@ns.route('/')
@ns.expect(parser_initiative)
class InitiativesCollection(Resource):

    def get(self):
        """Returns list of initiatives."""
        args = parser_initiative.parse_args(request)
        SearchesTracker.save_search(args, request.environ)
        # 'args' variable is gonna be adapted for searching after this line
        total, pages, page, per_page, initiatives = search_initiatives(args)
        return {
                'query_meta': {
                    'total': total,
                    'pages': pages,
                    'page': page,
                    'per_page': per_page
                    },
                'initiatives': initiatives.data
                }


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@api.response(404, 'Initiative not found.')
class InitiativeItem(Resource):

    @validate_id_as_hash
    def get(self, id):
        """Returns details of an initiative."""
        return get_initiative(id)
