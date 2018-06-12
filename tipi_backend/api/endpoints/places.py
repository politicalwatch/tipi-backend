import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.business import get_places

log = logging.getLogger(__name__)

ns = api.namespace('places', description='Operations related to places')



@ns.route('/')
class Places(Resource):

    def get(self):
        """Returns list of places."""
        return get_places()
