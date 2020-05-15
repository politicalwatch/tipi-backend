import logging

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.business import get_topics, get_topic
from tipi_backend.api.endpoints import cache


log = logging.getLogger(__name__)

ns = Namespace('topics', description='Operations related to topics')


@ns.route('/')
class TopicsCollection(Resource):

    @cache.cached()
    def get(self):
        """Returns list of topics."""
        return get_topics()


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Topic not found.')
class TopicItem(Resource):

    def get(self, id):
        """Returns details of a topic."""
        return get_topic(id)
