import logging

from flask import request, Response, stream_with_context
from requests import get
from flask_restplus import Namespace, Resource

log = logging.getLogger(__name__)

ns = Namespace('proxy', description='Operations related to proxy')

@ns.route('/')
@ns.response(200, description='Returns a proxied image.')
class Proxy(Resource):

    def get(self):
        url = request.args['url']
        req = get(url, stream = True)
        return Response(stream_with_context(req.iter_content()), content_type = req.headers['content-type'])
