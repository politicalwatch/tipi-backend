import logging

from flask_restplus import Namespace, Resource

from tipi_backend.api.business import get_voting


log = logging.getLogger(__name__)

ns = Namespace('voting', description='Operations related to votes')


@ns.route('/<initiative_id>')
@ns.param(name='initiative_id', description='Initiative ID', type=str, required=True, location=['path'], help='Invalid initiative ID')
@ns.response(404, 'Voting not found.')
class VotingItem(Resource):

    def get(self, initiative_id):
        """Returns details of a voting."""
        def to_reference(id):
            return id.replace('-', '/')
        try:
            log.info(to_reference(initiative_id))
            return get_voting(to_reference(initiative_id))
        except Exception as e:
            log.error(e)
            return {'Error': 'No votings found'}, 404
