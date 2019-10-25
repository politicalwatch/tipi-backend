import logging

from flask import request
from flask_restplus import Namespace, Resource

from tipi_backend.api.business import get_initiative_types


log = logging.getLogger(__name__)

ns = Namespace('initiative-types', description='Operations related to initiative types')



@ns.route('/')
class InitiativeTypes(Resource):

    def get(self):
        """Returns list of initiative types."""
        return get_initiative_types()
