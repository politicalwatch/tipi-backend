import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.business import get_initiative_status

log = logging.getLogger(__name__)

ns = api.namespace('initiative-status', description='Operations related to initiative status')



@ns.route('/')
class InitiativeStatus(Resource):

    def get(self):
        """Returns list of initiative status."""
        return get_initiative_status()
