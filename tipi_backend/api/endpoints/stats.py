import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.parsers import parser_stats
from tipi_backend.api.business import \
        get_overall_stats, \
        get_deputies_stats, \
        get_parliamentarygroups_stats, \
        get_latest_initiatives, \
        get_places_stats


log = logging.getLogger(__name__)

ns = api.namespace('stats', description='Operations related to stats')



@ns.route('/overall')
class OverallStats(Resource):

    def get(self):
        """Returns overall stats."""
        return get_overall_stats()

@ns.route('/deputies')
@ns.expect(parser_stats)
class DeputiesStats(Resource):

    def get(self):
        """Returns top ten deputies by topics (and/or subtopics)."""
        args = parser_stats.parse_args(request)
        return get_deputies_stats(args)

@ns.route('/parliamentarygroups')
@ns.expect(parser_stats)
class ParliamentaryGroupsStats(Resource):

    def get(self):
        """Returns ranking of parliamentary groups by topics (and/or subtopics)."""
        args = parser_stats.parse_args(request)
        return get_parliamentarygroups_stats(args)

@ns.route('/latest-initiatives')
@ns.expect(parser_stats)
class LatestStats(Resource):

    def get(self):
        """Returns latest initiatives by topics."""
        args = parser_stats.parse_args(request)
        return get_latest_initiatives(args)

@ns.route('/places')
@ns.expect(parser_stats)
class PlacesStats(Resource):

    def get(self):
        """Returns top five places by topics (and/or subtopics)."""
        args = parser_stats.parse_args(request)
        return get_places_stats(args)
