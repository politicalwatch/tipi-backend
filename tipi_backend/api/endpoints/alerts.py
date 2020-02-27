import logging
import json

from flask import request, abort
from flask_restplus import Namespace, Resource, fields

from tipi_backend.api.business import save_alert
from tipi_backend.api.endpoints import limiter
from tipi_backend.api.serializers import alert_model


log = logging.getLogger(__name__)

ns = Namespace('alerts', description='Operations related to alerts')

@ns.route('')
@ns.doc(False)
@ns.expect(alert_model)
class AlertCollection(Resource):
    decorators = [
        limiter.limit('10/hour', methods=['POST'])
    ]

    @ns.response(201, 'Alert successfully created.')
    def post(self):
        ''' Create a new alert '''
        try:
            save_alert(ns.payload)
        except Exception as e:
            abort(500)

