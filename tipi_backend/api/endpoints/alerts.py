import logging
import json

from flask import request
from flask_restplus import Resource, fields

from tipi_backend.api.business import save_alert
from tipi_backend.api.restplus import api
from tipi_backend.api.serializers import alert_model
from tipi_backend.api.parsers import parser_initiative


log = logging.getLogger(__name__)

ns = api.namespace('alerts', description='Operations related to alerts')

@ns.route('/')
class AlertCollection(Resource):

    @ns.expect(alert_model)
    @ns.response(201, 'Alert successfully created.')
    def post(self):
        ''' Create a new alert '''
        save_alert(api.payload)
