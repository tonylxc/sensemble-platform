def test_ingest_and_query(client, make_user, make_device):
    h = make_user("stu3")
    did, tok = make_device(h, "devx")
    r = client.post("/api/v1/data",
                    json=[{"metric": "temperature", "value": 23.5}, {"metric": "humidity", "value": 40}],
                    headers={"X-Device-Id": did, "X-Device-Token": tok})
    assert r.status_code == 200 and r.json()["received"] == 2

    q = client.get("/api/v1/data", params={"device_id": did, "metric": "temperature"}, headers=h)
    assert q.status_code == 200
    rows = q.json()
    assert len(rows) == 1 and rows[0]["value"] == 23.5


def test_ingest_bad_token(client, make_user, make_device):
    h = make_user("stu4")
    did, _ = make_device(h, "devy")
    r = client.post("/api/v1/data", json=[{"metric": "t", "value": 1}],
                    headers={"X-Device-Id": did, "X-Device-Token": "WRONG"})
    assert r.status_code == 401


def test_ingest_missing_headers(client):
    assert client.post("/api/v1/data", json=[{"metric": "t", "value": 1}]).status_code == 401


def test_query_requires_login(client):
    assert client.get("/api/v1/data", params={"device_id": "x"}).status_code == 401
