import logging
import traceback
from os import environ as env


from flask import current_app
from flask_restx import Api
from tipi_data import DoesNotExist



log = logging.getLogger(__name__)

name = env.get('NAME', 'test')
desc = env.get('DESCRIPTION', "This document includes all the methods that the {} API offers its users.").format(name)
version = env.get('VERSION', '1.0')
api = Api(
    title='{} API Documentation'.format(name),
    description=desc,
    version=version
)

# Dirty monkey patching to fix error on the Swagger UI.
class ApiFixed(Api):
    specs_url = 'https://api.quehacenlosdiputados.es/swagger.json'
api.__class__ = ApiFixed

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    log.exception(message)

    if not current_app.config.FLASK_DEBUG:
        return {'message': message}, 500


@api.errorhandler(DoesNotExist)
def database_not_found_error_handler(e):
    log.warning(traceback.format_exc())
    return {'message': 'Resource not found.'}, 404
