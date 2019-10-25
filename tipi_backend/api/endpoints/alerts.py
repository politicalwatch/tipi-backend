import logging
import json

from flask import request, abort
from flask_restplus import Namespace, Resource, fields

from tipi_backend.api.business import save_alert
from tipi_backend.api.serializers import alert_model
from tipi_backend.api.parsers import parser_initiative
from tipi_backend.settings import USE_ALERTS


log = logging.getLogger(__name__)

ns = Namespace('alerts', description='Operations related to alerts')

if USE_ALERTS:
    @ns.route('/')
    @ns.doc(False)
    class AlertCollection(Resource):

        @ns.expect(alert_model)
        @ns.response(201, 'Alert successfully created.')
        def post(self):
            ''' Create a new alert '''
            try:
                save_alert(ns.payload)
            except Exception as e:
                abort(500)

