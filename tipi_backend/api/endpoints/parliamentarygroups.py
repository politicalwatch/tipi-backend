import logging

from flask import request
from flask_restx import Namespace, Resource

from tipi_backend.api.parsers import parser_authors
from tipi_backend.api.business import get_parliamentarygroups, get_parliamentarygroup
from tipi_backend.api.endpoints import cache
from tipi_backend.settings import Config

log = logging.getLogger(__name__)

ns = Namespace('parliamentary-groups', description='Operations related to parliamentary groups')


@ns.route('/')
@ns.expect(parser_authors)
class ParliamentaryGroupsCollection(Resource):

    def get(self):
        """Returns list of parliamentary groups."""
        args = parser_authors.parse_args(request)
        cache_key = Config.CACHE_GROUPS
        parliamentary_groups = cache.get(cache_key)
        if parliamentary_groups is None:
            parliamentary_groups = get_parliamentarygroups(args)
            cache.set(cache_key, parliamentary_groups, timeout=60*60)
        return parliamentary_groups


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Parliamentary group not found.')
class ParliamentaryGroupItem(Resource):

    def get(self, id):
        """Returns details of a parliamentary group."""
        try:
            return get_parliamentarygroup(id)
        except Exception as e:
            log.error(e)
            return {'Error': 'No parliamentary group found'}, 404
