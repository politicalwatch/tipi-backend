import json

from tipi_backend.settings import Config


def test_rate_limit_alerts(client):
    """POST /alerts is limited to 10/hour; POST /tagger/ is unlimited."""
    data = json.dumps({"email": "foo@bar.com", "search": '{"topic": "bar"}'})
    headers = {"Content-Type": "application/json"}

    for _ in range(10):
        res = client.post("/tagger/", data={"text": "example"})
        assert res.status_code == 200

        res = client.post("/alerts", data=data, headers=headers)
        assert res.status_code == 200

    res = client.post("/alerts", data=data, headers=headers)
    assert res.status_code == 429
