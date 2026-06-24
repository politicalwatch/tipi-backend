"""Tier-2 live-data smoke tests (``-m integration``).

These pin the **connection + data contract** against qhld-infra's prod-copy Mongo —
read-only, never mutating. They are intentionally separate from the Tier-1 endpoint
tests so a Mongo/data problem fails *here*, not in the tagger logic tests.

Run with ``MONGO_*`` pointing at the prod copy, e.g. from the host:
    MONGO_HOST=localhost MONGO_PORT=62884 MONGO_USER=qhld MONGO_PASSWORD=… \
        uv run pytest -m integration
or inside the qhld-infra ``qhld-backend`` container (``MONGO_HOST=mongo``).
"""

import pytest

from tipi_data import db
from tipi_data.repositories.knowledgebases import KnowledgeBases

from tipi_backend.api.business import get_tags, get_topics

pytestmark = pytest.mark.integration

STABLE_KBS = {"politicas", "ods"}


def test_get_tags_live_wellformed():
    tags = get_tags()
    assert tags, "live KB returned no tags"
    sample = tags[0]
    assert {"topic", "subtopic", "tag", "knowledgebase", "public", "compiletag"} <= sample.keys()


def test_public_knowledgebases_include_stable():
    kbs = set(KnowledgeBases.get_public())
    assert STABLE_KBS <= kbs, f"expected {STABLE_KBS} among public KBs, got {kbs}"


def test_public_topics_present():
    assert get_topics(), "no public topics in live DB"


@pytest.mark.parametrize("collection", ["topics", "deputies", "parliamentarygroups", "initiatives"])
def test_core_collections_nonempty(collection):
    assert db[collection].estimated_document_count() > 0, f"{collection} is empty"
