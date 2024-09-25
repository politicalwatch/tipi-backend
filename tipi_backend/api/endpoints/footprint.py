import logging

from flask import request
from flask_restx import Namespace, Resource

from tipi_backend.api.parsers import parser_footprint_by_topic, \
        parser_footprint_by_deputy, \
        parser_footprint_by_parliamentarygroup
from tipi_backend.api.business import get_footprint_by_topic, \
        get_max_footprint_by_all_topics, \
        get_footprint_by_deputy, \
        get_footprint_by_parliamentarygroup


log = logging.getLogger(__name__)

ns = Namespace('footprint', description='Operations related to parliamentary footprint')


@ns.route('/by-topic')
@ns.expect(parser_footprint_by_topic)
class FootprintByTopic(Resource):
    def get(self):
        """Returns footprint by a specific topic."""
        args = parser_footprint_by_topic.parse_args(request)
        try:
            return get_footprint_by_topic(args)
        except Exception as e:
            log.error(e)
            return {'Error': f"No footprint by topic {args['topic']} found."}, 404


@ns.route('/max-by-all-topics')
class FootprintMaxByAllTopics(Resource):
    def get(self):
        """Returns max deputy and parliamentarygroup's footprint by all topics."""
        try:
            return get_max_footprint_by_all_topics()
        except Exception as e:
            log.error(e)
            return {'Error': f"No footprints found."}, 404


@ns.route('/by-deputy')
@ns.expect(parser_footprint_by_deputy)
class FootprintByDeputy(Resource):
    def get(self):
        """Returns footprint by a specific deputy."""
        args = parser_footprint_by_deputy.parse_args(request)
        try:
            return get_footprint_by_deputy(args)
        except Exception as e:
            log.error(e)
            return {'Error': f"No footprint by deputy {args['deputy']} found."}, 404


@ns.route('/by-parliamentarygroup')
@ns.expect(parser_footprint_by_parliamentarygroup)
class FootprintByParliamentaryGroup(Resource):
    def get(self):
        """Returns footprint by a specific parliamentary group."""
        args = parser_footprint_by_parliamentarygroup.parse_args(request)
        try:
            return get_footprint_by_parliamentarygroup(args)
        except Exception as e:
            log.error(e)
            return {'Error': f"No footprint by parliamentary group {args['parliamentarygroup']} found."}, 404
