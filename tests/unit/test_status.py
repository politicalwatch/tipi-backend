"""Tier-1 tests for the root status endpoint — no Mongo.

``GET /`` reports how fresh the data is from the timestamps the engine stamps when it
rewrites a dataset (the same moment it drops the stale cached responses). The
repository is faked, so the timestamp handling is what is under test: Mongo hands
back **naive** UTC datetimes (the client is deliberately not ``tz_aware``), and the
endpoint must not serve those without a zone.
"""

from datetime import datetime, timedelta, timezone

import pytest

from tipi_backend.api import business

pytestmark = pytest.mark.unit


@pytest.fixture
def updates(monkeypatch):
    """Make ``DatasetUpdates.get_all`` return whatever a test sets."""
    stored = {}
    monkeypatch.setattr(business.DatasetUpdates, "get_all", lambda: stored)
    return stored


def test_root_reports_the_end_of_the_last_complete_run(client, updates):
    updates.update({
        "deputies": datetime(2026, 7, 31, 2, 14, 7),
        "parliamentary-groups": datetime(2026, 7, 31, 2, 14, 9),
        "initiatives": datetime(2026, 7, 30, 23, 41, 55),
        "extraction": datetime(2026, 7, 31, 2, 55, 1),
    })

    body = client.get("/").json()

    assert body["status"] == "ok"
    assert body["last_updated"] == "2026-07-31T02:55:01Z"
    # "extraction" is the pipeline, not a dataset — it does not belong in the breakdown.
    assert body["datasets"] == {
        "deputies": "2026-07-31T02:14:07Z",
        "initiatives": "2026-07-30T23:41:55Z",
        "parliamentary-groups": "2026-07-31T02:14:09Z",
    }
    # the pre-existing payload is untouched
    assert body["docs"] == "/docs"
    assert body["openapi"] == "/openapi.json"


def test_a_stalled_run_does_not_look_fresh(client, updates):
    # The pipeline broke after the deputies step, so today's date is on a dataset but
    # no run completed. Reporting the newest dataset here is exactly the lie the
    # completion stamp exists to stop.
    updates.update({
        "deputies": datetime(2026, 7, 31, 2, 14, 7),
        "extraction": datetime(2026, 7, 28, 2, 55, 1),
    })

    assert client.get("/").json()["last_updated"] == "2026-07-28T02:55:01Z"


def test_without_a_completion_stamp_it_falls_back_to_the_newest_dataset(client, updates):
    # Environments that don't run the pipeline (dev) and any engine older than the
    # completion stamp keep the previous behaviour instead of reporting nothing.
    updates.update({
        "deputies": datetime(2026, 7, 31, 2, 14, 7),
        "initiatives": datetime(2026, 7, 30, 23, 41, 55),
    })

    body = client.get("/").json()

    assert body["last_updated"] == "2026-07-31T02:14:07Z"
    assert set(body["datasets"]) == {"deputies", "initiatives"}


def test_root_reports_unknown_before_the_first_extraction(client, updates):
    body = client.get("/").json()

    assert body["status"] == "ok"
    assert body["last_updated"] is None
    assert body["datasets"] == {}


def test_root_stays_up_when_the_bookkeeping_cannot_be_read(client, monkeypatch):
    def unreachable():
        raise ConnectionError("no mongo")

    monkeypatch.setattr(business.DatasetUpdates, "get_all", unreachable)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["last_updated"] is None


def test_already_aware_timestamps_are_normalised_to_utc(client, updates):
    # Defensive: if the Mongo client is ever made tz_aware, or a value arrives with
    # an offset, the response must still be a single comparable UTC instant.
    madrid_summer = timezone(timedelta(hours=2))
    updates["deputies"] = datetime(2026, 7, 31, 4, 14, 7, tzinfo=madrid_summer)

    body = client.get("/").json()

    assert body["datasets"]["deputies"] == "2026-07-31T02:14:07Z"
