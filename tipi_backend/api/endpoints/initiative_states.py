import logging

from flask import request
from flask_restplus import Resource
from tipi_backend.api.restplus import api
from tipi_backend.api.business import get_initiative_states

log = logging.getLogger(__name__)

ns = api.namespace('initiative-states', description='Operations related to initiative states')



@ns.route('/')
class InitiativeStates(Resource):

    def get(self):
        """Returns list of initiative states."""
        return get_initiative_states()
