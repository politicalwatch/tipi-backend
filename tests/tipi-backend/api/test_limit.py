def test_rate_limit_alerts(client):
    """POST /alerts is limited to 10/hour; POST /tagger/ is unlimited."""
    payload = {"email": "foo@bar.com", "search": '{"topic": "bar"}'}

    for _ in range(10):
        res = client.post("/tagger/", data={"text": "example"})
        assert res.status_code == 200

        res = client.post("/alerts", json=payload)
        assert res.status_code == 200

    res = client.post("/alerts", json=payload)
    assert res.status_code == 429
