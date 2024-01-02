import logging

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.parsers import \
        parser_stats, \
        parser_stats_by_topic, \
        parser_stats_by_group, \
        parser_kb
from tipi_backend.api.business import \
        get_overall_stats, \
        get_lastdays_stats, \
        get_deputies_stats, \
        get_parliamentarygroups_stats, \
        get_places_stats, \
        get_topics_by_parliamentarygroup_stats, \
        get_by_week_stats, \
        get_topics_by_week_stats


log = logging.getLogger(__name__)

ns = Namespace('stats', description='Operations related to stats')


@ns.route('/overall')
@ns.expect(parser_kb)
class OverallStats(Resource):

    def get(self):
        """Returns overall stats."""
        args = parser_kb.parse_args(request)
        return get_overall_stats(args)

@ns.route('/lastdays')
class LastdaysStats(Resource):

    def get(self):
        """Returns last days stats."""
        args = parser_kb.parse_args(request)
        return get_lastdays_stats(args)

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

@ns.route('/places')
@ns.expect(parser_stats)
class PlacesStats(Resource):

    def get(self):
        """Returns top five places by topics (and/or subtopics)."""
        args = parser_stats.parse_args(request)
        return get_places_stats(args)

@ns.route('/topics-by-parliamentarygroup')
@ns.expect(parser_stats_by_group)
class TopicsByParliamentaryGroupStats(Resource):

    def get(self):
        """Returns ranking of topics by parliamentary group."""
        args = parser_stats_by_group.parse_args(request)
        return get_topics_by_parliamentarygroup_stats(args)

@ns.route('/by-week')
class ByWeekStats(Resource):

    def get(self):
        """Returns initiatives by week stats."""
        return get_by_week_stats()

@ns.route('/topics-by-week')
@ns.expect(parser_stats_by_topic)
class TopicsByWeekStats(Resource):

    def get(self):
        """Returns topics' initiatives by week stats."""
        args = parser_stats_by_topic.parse_args(request)
        return get_topics_by_week_stats(args)
