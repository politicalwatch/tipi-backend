import logging
import json

from flask import request
from flask_restplus import Namespace, Resource
from tipi_data.models.searches_tracker import SearchesTracker

from tipi_backend.api.parsers import parser_initiative
from tipi_backend.api.business import search_initiatives, get_content_initiative, get_initiative


log = logging.getLogger(__name__)

ns = Namespace('initiatives', description='Operations related to initiatives')



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
@ns.response(404, 'Initiative not found.')
class InitiativeItem(Resource):

    def get(self, id):
        """Returns details of an initiative."""
        return get_initiative(id)

@ns.route('/<id>/content')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Initiative not found.')
class InitiativeContentItem(Resource):

    def get(self, id):
        """Returns details of an initiative."""
        return get_content_initiative(id)
