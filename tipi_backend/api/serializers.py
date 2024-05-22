from flask_restx import fields
from tipi_backend.api.restplus import api


alert_model = api.model('alert', {
    'email': fields.String(required=True, description='User email to reveive alerts'),
    'search': fields.String(required=True, description='Serialized search')
})

scanned_model = api.model('scanned', {
    'title': fields.String(required=True, description="Scanned document's title"),
    'expiration': fields.String(required=False, description="Scanned document's expiration date"),
    'excerpt': fields.String(required=True, description="Scanned document's excerpt"),
    'result': fields.String(required=True, description='Serialized result')
})
