import logging
import json

from flask import request
from flask_restx import Namespace, Resource
from tipi_data.models.searches_tracker import SearchesTracker

from tipi_backend.api.parsers import parser_initiative, parser_initiatives
from tipi_backend.api.business import (
    search_initiatives,
    get_initiative,
)


log = logging.getLogger(__name__)

ns = Namespace("initiatives", description="Operations related to initiatives")


@ns.route("/")
@ns.expect(parser_initiatives)
class InitiativesCollection(Resource):

    def get(self):
        """Returns list of initiatives."""
        args = parser_initiatives.parse_args(request)
        SearchesTracker.save_search(args, request.environ)
        # 'args' variable is gonna be adapted for searching after this line
        total, pages, page, per_page, initiatives = search_initiatives(args)
        return {
            "query_meta": {
                "total": total,
                "pages": pages,
                "page": page,
                "per_page": per_page,
            },
            "initiatives": initiatives,
        }


@ns.route("/<id>")
@ns.param(
    name="id",
    description="Identifier",
    type=str,
    required=True,
    location=["path"],
    help="Invalid identifier",
)
@ns.response(404, "Initiative not found.")
@ns.expect(parser_initiative)
class InitiativeItem(Resource):

    def get(self, id):
        """Returns details of an initiative."""
        args = parser_initiative.parse_args(request)
        try:
            return get_initiative(id=id, params=args)
        except Exception as e:
            print(e)
            return {"Error": "No initiative found"}, 404
