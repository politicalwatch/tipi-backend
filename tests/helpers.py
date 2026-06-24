"""Test helpers shared across tiers."""

import json
from pathlib import Path

from tipi_data.repositories.tags import compile_tag

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_knowledgebase():
    """The self-contained ``politicas`` + ``ods`` KB slice used by Tier-1 tests.

    Raw-regex topic docs (``{name, knowledgebase, public, tags}``) exported from a
    real prod-copy KB — no Mongo needed to read it.
    """
    with open(FIXTURES_DIR / "knowledgebase.json") as f:
        return json.load(f)


def build_tags_from_fixture(topics):
    """Mirror ``tipi_data.repositories.tags.Tags.get_all()`` over a fixture instead of
    Mongo, reusing the real ``compile_tag`` (incl. ``shuffle`` permutations) so the
    output is exactly what ``extract_tags_from_text`` expects — each tag carries a
    precompiled ``compiletag`` regex.
    """
    tags = []
    for topic in topics:
        for tag in topic["tags"]:
            compiled = compile_tag(topic, tag)
            if compiled:
                tags += compiled
    return tags


def read_scanner_text(filename):
    with open(FIXTURES_DIR / "scanner_text" / filename) as f:
        return f.read()
