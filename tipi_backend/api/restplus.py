import logging
import traceback


from flask_restplus import Api
from mongoengine.queryset import DoesNotExist
from tipi_backend import settings



log = logging.getLogger(__name__)

api = Api(
        title='TIPI API Documentation',
        description='This document includes all the methods that the TIPI API offers its users.',
        version='1.0'
        )


@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    log.exception(message)

    if not settings.FLASK_DEBUG:
        return {'message': message}, 500


@api.errorhandler(DoesNotExist)
def database_not_found_error_handler(e):
    log.warning(traceback.format_exc())
    return {'message': 'Resource not found.'}, 404
