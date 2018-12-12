from flask_restplus import fields
from tipi_backend.api.restplus import api


alert_model = api.model('alert', {
    'email': fields.String(required=True, description='User email to reveive alerts'),
    'search': fields.String(required=True, description='Serialized search')
})
