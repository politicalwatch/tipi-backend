import logging.config

import os
from flask import Flask, Blueprint
from flask_cors import CORS

from tipi_backend import settings
from tipi_backend.api.endpoints.topics import ns as topics_namespace
from tipi_backend.api.endpoints.deputies import ns as deputies_namespace
from tipi_backend.api.endpoints.parliamentarygroups import ns as parliamentarygroups_namespace
from tipi_backend.api.endpoints.initiatives import ns as initiatives_namespace
from tipi_backend.api.endpoints.places import ns as places_namespace
from tipi_backend.api.endpoints.initiative_types import ns as initiativetypes_namespace
from tipi_backend.api.endpoints.initiative_status import ns as initiativestatus_namespace
from tipi_backend.api.restplus import api
from tipi_backend.database import db


app = Flask(__name__)
logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)


def configure_app(flask_app):
    flask_app.config['SERVER_NAME'] = settings.FLASK_SERVER_NAME
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = settings.RESTPLUS_SWAGGER_UI_DOC_EXPANSION
    flask_app.config['RESTPLUS_VALIDATE'] = settings.RESTPLUS_VALIDATE
    flask_app.config['RESTPLUS_MASK_SWAGGER'] = settings.RESTPLUS_MASK_SWAGGER
    flask_app.config['ERROR_404_HELP'] = settings.RESTPLUS_ERROR_404_HELP
    flask_app.config['MONGODB_SETTINGS'] = {
            'host': settings.MONGO_HOST,
            'port': settings.MONGO_PORT,
            'db': settings.MONGO_DBNAME,
            'username': settings.MONGO_USERNAME,
            'password': settings.MONGO_PASSWORD
            }


def initialize_app(flask_app):
    configure_app(flask_app)

    db.init_app(flask_app)

    blueprint = Blueprint('api', __name__)
    CORS(blueprint)
    api.init_app(blueprint)
    api.add_namespace(topics_namespace)
    api.add_namespace(deputies_namespace)
    api.add_namespace(parliamentarygroups_namespace)
    api.add_namespace(initiatives_namespace)
    api.add_namespace(places_namespace)
    api.add_namespace(initiativetypes_namespace)
    api.add_namespace(initiativestatus_namespace)
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
