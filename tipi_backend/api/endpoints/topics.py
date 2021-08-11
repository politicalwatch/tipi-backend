import logging

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.business import get_topics, get_topic
from tipi_backend.api.endpoints import cache
from tipi_backend.api.parsers import parser_topic


log = logging.getLogger(__name__)

ns = Namespace('topics', description='Operations related to topics')


@ns.route('/')
@ns.expect(parser_topic)
class TopicsCollection(Resource):

    @cache.cached()
    def get(self):
        """Returns list of topics."""
        args = parser_topic.parse_args(request)

        if 'knowledgebase' in args and args['knowledgebase'] is not None:
            kb = args['knowledgebase']
            return get_topics(kb.split(','))

        return get_topics()


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Topic not found.')
@ns.expect(parser_topic)
class TopicItem(Resource):

    def get(self, id):
        """Returns details of a topic."""
        try:
            return get_topic(id)
        except Exception:
            return {'Error': 'No topic found'}, 404
