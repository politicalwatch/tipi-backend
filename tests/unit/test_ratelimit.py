"""Tier-1 rate-limit test — no Mongo, no Redis.

slowapi's limiter already uses in-memory storage, and ``save_alert`` (the only Mongo
write + email-task trigger behind ``/alerts``) is mocked out, so this isolates the
limiter: ``POST /alerts`` is capped at 10/hour.
"""

import pytest

pytestmark = pytest.mark.unit


def test_rate_limit_alerts(client, monkeypatch):
    monkeypatch.setattr(
        "tipi_backend.api.endpoints.alerts.save_alert", lambda payload: None
    )
    payload = {"email": "foo@bar.com", "search": '{"topic": "bar"}'}

    for _ in range(10):
        res = client.post("/alerts", json=payload)
        assert res.status_code == 200

    res = client.post("/alerts", json=payload)
    assert res.status_code == 429
