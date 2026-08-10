"""Tier-1 (no-infra) fixtures."""

import pytest

from tipi_data import DoesNotExist

from tipi_backend.api import business
from tipi_backend.api.ratelimit import limiter


class _NoAlignments:
    """A corpus in which nothing has been aligned — what almost every speech is."""

    @staticmethod
    def summary(id, lang):
        return None

    @staticmethod
    def summaries(id, langs):
        return []

    @staticmethod
    def get(id, lang):
        raise DoesNotExist(id)


@pytest.fixture(autouse=True)
def no_alignments():
    """Every speech detail asks whether the speech has subtitles, and Tier-1 has no
    Mongo to answer with — without this the question would hang on server selection
    in every test that fetches a speech. Tests about subtitles replace it.

    Patched by hand rather than through ``monkeypatch``: requesting that fixture here
    would make it the *first* one set up and so the last undone, which reverses the
    teardown order other modules' autouse fixtures were written against.
    """
    original = business.SpeechAlignments
    business.SpeechAlignments = _NoAlignments
    yield
    business.SpeechAlignments = original


@pytest.fixture(autouse=True)
def reset_limiter():
    """slowapi's limiter uses process-wide in-memory storage; reset it around every
    test so rate-limit counts never bleed between tests."""
    limiter.reset()
    yield
    limiter.reset()
