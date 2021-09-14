import logging
import json

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.parsers import parser_all_initiatives
from tipi_backend.api.business import search_all_initiatives


log = logging.getLogger(__name__)

ns = Namespace('all-initiatives', description='Operations related to initiatives')


@ns.route('/')
@ns.expect(parser_all_initiatives)
class AllInitiativesCollection(Resource):

    def get(self):
        """Returns list of initiatives."""
        args = parser_all_initiatives.parse_args(request)
        total, pages, page, per_page, initiatives = search_all_initiatives(args)
        return {
                'query_meta': {
                    'total': total,
                    'pages': pages,
                    'page': page,
                    'per_page': per_page
                    },
                'initiatives': initiatives.data
                }
