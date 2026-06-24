"""Tier-2 tagger sentinels (``-m integration``).

"Does the *real* KB still produce sane tags?" — a small known-subset of high-confidence
hits, checked against the **live** KB (all public knowledgebases). These run the tagging
directly off ``get_tags()`` (live Mongo) + the qhld-tasks tagger, deliberately bypassing
the HTTP/cache layer so this fails for a *data* reason, not an endpoint one.

Known-subset only (never exhaustive) — kept cheap and non-brittle. Mirrors the Tier-1
``SANITY_HITS`` so the two should agree on the obvious pairs, confirming the offline
fixture is a faithful slice of the live ``politicas``/``ods`` KBs.
"""

import codecs
import pickle

import pytest

import tipi_tasks
from tipi_backend.api.business import get_tags
from tests.helpers import read_scanner_text

pytestmark = pytest.mark.integration

SENTINELS = {
    "w500.txt": ("ODS 3 Salud y bienestar", "Aborto"),
    "w2000.txt": ("ODS 13 Acción por el clima", "Cambio climático"),
    "w5000.txt": ("Personas mayores", "Persona mayor"),
}


@pytest.fixture(scope="module")
def live_tags_encoded():
    """The live KB tags, base64-pickled exactly as the endpoint passes them."""
    return codecs.encode(pickle.dumps(get_tags()), "base64").decode()


@pytest.mark.parametrize("filename", SENTINELS)
def test_real_kb_sentinels(live_tags_encoded, filename):
    result = tipi_tasks.tagger.extract_tags_from_text(
        read_scanner_text(filename), live_tags_encoded
    )["result"]

    by_topic = {}
    for tag in result["tags"]:
        by_topic.setdefault(tag["topic"], set()).add(tag["tag"])

    topic, expected_tag = SENTINELS[filename]
    assert expected_tag in by_topic.get(topic, set()), (
        f"{filename}: expected sentinel {expected_tag!r} under topic {topic!r} "
        "against the live KB"
    )
