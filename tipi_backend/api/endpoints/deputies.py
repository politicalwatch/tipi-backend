import logging

from flask import request
from flask_restx import Namespace, Resource

from tipi_backend.api.parsers import parser_authors
from tipi_backend.api.business import get_deputies, get_deputy, get_deputies_birthdays
from tipi_backend.api.endpoints import cache
from tipi_backend.settings import Config


log = logging.getLogger(__name__)

ns = Namespace('deputies', description='Operations related to deputies')


@ns.route('/')
@ns.expect(parser_authors)
class DeputiesCollection(Resource):

    def get(self):
        """Returns list of active deputies."""
        args = parser_authors.parse_args(request)
        cache_key = Config.CACHE_DEPUTIES
        deputies = cache.get(cache_key)
        if deputies is None:
            deputies = get_deputies(args)
            cache.set(cache_key, deputies, timeout=60*60)
        return deputies


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Deputy not found.')
class DeputyItem(Resource):

    def get(self, id):
        """Returns details of a deputy."""
        try:
            return get_deputy(id)
        except Exception as e:
            log.error(e)
            return {'Error': 'No deputy found'}, 404


@ns.route('/birthdays')
class DeputiesBirthdaysCollection(Resource):

    def get(self):
        """Returns a list of deputies whose birthday is today"""
        return get_deputies_birthdays()
