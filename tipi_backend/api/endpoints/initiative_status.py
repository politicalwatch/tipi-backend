import logging

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.business import get_initiative_status


log = logging.getLogger(__name__)

ns = Namespace('initiative-status', description='Operations related to initiative status')


@ns.route('/')
class InitiativeStatus(Resource):

    def get(self):
        """Returns list of initiative status."""
        return get_initiative_status()
