import logging

from flask import request
from flask_restx import Namespace, Resource

from tipi_backend.api.business import get_topics, get_topic
from tipi_backend.api.endpoints import cache
from tipi_backend.api.parsers import parser_kb


log = logging.getLogger(__name__)

ns = Namespace('topics', description='Operations related to topics')


@ns.route('/')
@ns.expect(parser_kb)
class TopicsCollection(Resource):

    def get(self):
        """Returns list of topics."""
        args = parser_kb.parse_args(request)

        if 'knowledgebase' in args and args['knowledgebase'] is not None:
            kb = args['knowledgebase']
            return get_topics(kb.split(','))

        return get_topics()


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Topic not found.')
class TopicItem(Resource):

    def get(self, id):
        """Returns details of a topic."""
        try:
            return get_topic(id)
        except Exception as e:
            log.error(e)
            return {'Error': 'No topic found'}, 404
