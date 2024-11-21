import logging

from flask_restx import Namespace, Resource

from tipi_backend.api.business import get_voting, get_voting_outliers
from tipi_backend.api.parsers import parser_voting_outliers


log = logging.getLogger(__name__)

ns = Namespace("voting", description="Operations related to votes")


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
            return {"Error": "No votings found"}, 404


ns = Namespace(
    "voting-outliers",
    description="Operations related to votes from outliers (people who vote differently from their group)",
)


@ns.route("/")
@ns.expect(parser_voting_outliers)
@ns.response(404, "Voting not found.")
class VotingOutlierItem(Resource):
    def get(self, exclude_group=None):
        """Returns details of a voting."""
        try:
            log.info("Voting outliers called")
            if exclude_group is None:
                return get_voting_outliers()
            return get_voting_outliers(exclude_group)
        except Exception as e:
            log.error(e)
            return {"Error": "No voting outliers found"}, 404
