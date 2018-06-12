import logging

from flask import request
from flask_restplus import Resource
from mongoengine.queryset import DoesNotExist
from tipi_backend.api.restplus import api
from tipi_backend.api.business import get_topics, get_topic
from tipi_backend.api.validators import validate_id_as_hash

log = logging.getLogger(__name__)

ns = api.namespace('topics', description='Operations related to topics')


@ns.route('/')
class TopicsCollection(Resource):

    def get(self):
        """Returns list of topics."""
        return get_topics()


@ns.route('/<id>')
@ns.param(name='id', description='Identifier', type=str, required=True, location=['path'], help='Invalid identifier')
@api.response(404, 'Topic not found.')
class TopicItem(Resource):

    @validate_id_as_hash
    def get(self, id):
        """Returns details of a topic."""
        return get_topic(id)
