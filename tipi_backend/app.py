import logging.config

import os
from flask import Flask, Blueprint
from werkzeug.contrib.fixers import ProxyFix
from flask_cors import CORS

from tipi_backend import settings
from tipi_backend.manage_alerts_by_email import alerts_by_email_blueprint
from tipi_backend.api.endpoints.topics import ns as topics_namespace
from tipi_backend.api.endpoints.deputies import ns as deputies_namespace
from tipi_backend.api.endpoints.parliamentarygroups import ns as parliamentarygroups_namespace
from tipi_backend.api.endpoints.initiatives import ns as initiatives_namespace
from tipi_backend.api.endpoints.places import ns as places_namespace
from tipi_backend.api.endpoints.initiative_types import ns as initiativetypes_namespace
from tipi_backend.api.endpoints.initiative_status import ns as initiativestatus_namespace
from tipi_backend.api.endpoints.stats import ns as stats_namespace
from tipi_backend.api.endpoints.labels import ns as labels_namespace
from tipi_backend.api.endpoints.alerts import ns as alerts_namespace
from tipi_backend.api.restplus import api


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)


def configure_app(flask_app):
    flask_app.config['SERVER_NAME'] = settings.FLASK_SERVER_NAME
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = settings.RESTPLUS_SWAGGER_UI_DOC_EXPANSION
    flask_app.config['RESTPLUS_VALIDATE'] = settings.RESTPLUS_VALIDATE
    flask_app.config['RESTPLUS_MASK_SWAGGER'] = settings.RESTPLUS_MASK_SWAGGER
    flask_app.config['ERROR_404_HELP'] = settings.RESTPLUS_ERROR_404_HELP


def add_namespaces(app, api):
    namespaces = [ns for ns in [
            topics_namespace,
            deputies_namespace,
            parliamentarygroups_namespace,
            initiatives_namespace,
            places_namespace,
            initiativetypes_namespace,
            initiativestatus_namespace,
            stats_namespace,
            labels_namespace
            ] if ns.name not in settings.EXCLUDE_NAMESPACES]
    for ns in namespaces:
        api.add_namespace(ns)

    if settings.USE_ALERTS:
        api.add_namespace(alerts_namespace)
        app.register_blueprint(alerts_by_email_blueprint)


def initialize_app(flask_app):
    configure_app(flask_app)
    blueprint = Blueprint('api', __name__)
    CORS(blueprint)
    api.init_app(blueprint)
    add_namespaces(flask_app, api)
    flask_app.register_blueprint(blueprint)


def main():
    initialize_app(app)
    log.info('>>>>> Starting development server at http://{}/ <<<<<'.format(app.config['SERVER_NAME']))
    app.run(
            host=settings.IP,
            port=settings.PORT,
            debug=settings.FLASK_DEBUG
            )


if __name__ == "__main__":
    main()
