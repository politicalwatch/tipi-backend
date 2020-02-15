import logging.config

import os
from os import environ as env
from flask import Flask, Blueprint
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

from tipi_backend.settings import Config
from tipi_backend.manage_alerts_by_email import alerts_by_email_blueprint
from tipi_backend.api.endpoints import cache, limiter
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
from tipi_backend.database import db


def create_app(config=Config):
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_object(config)
    initialize_app(app)

    logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
    logging.config.fileConfig(logging_conf_path)
    log = logging.getLogger(__name__)
    log.info('>>>>> Starting development server at http://{}/ <<<<<'.format(app.config['SERVER_NAME']))
    return app


def add_namespaces(app):
    namespaces = [topics_namespace,
                  deputies_namespace,
                  parliamentarygroups_namespace,
                  initiatives_namespace,
                  places_namespace,
                  initiativetypes_namespace,
                  initiativestatus_namespace,
                  stats_namespace,
                  labels_namespace
    ]
    if env.get('USE_ALERTS', False):
        namespaces.append(alerts_namespace)

    for ns in namespaces:
        if ns.name in env.get('EXCLUDE_NAMESPACES', []):
            continue
        api.add_namespace(ns)


def initialize_app(app):
    db.init_app(app)
    cache.init_app(app, config=Config.CACHE)
    limiter.init_app(app)
    blueprint = Blueprint('api', __name__)
    CORS(blueprint)
    api.init_app(blueprint)
    add_namespaces(app)
    app.register_blueprint(blueprint)
    if env.get('USE_ALERTS', False):
        app.register_blueprint(alerts_by_email_blueprint)


def main():
    app = create_app(Config)
    app.run(
        host=app.config['IP'],
        port=app.config['PORT'],
        debug=app.config['FLASK_DEBUG']
    )


if __name__ == "__main__":
    main()
