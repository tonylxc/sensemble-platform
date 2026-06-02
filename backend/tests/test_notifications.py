import datetime as dt


def _make_dataset(client, sh, did, tok):
    client.post("/api/v1/data", json=[{"metric": "temperature", "value": 1}],
                headers={"X-Device-Id": did, "X-Device-Token": tok})
    end = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)).isoformat()
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
    return client.post("/api/v1/datasets",
                       json={"name": "通知测试集", "device_id": did, "start": start, "end": end},
                       headers=sh).json()["dataset_id"]


def test_review_creates_notification(client, make_user, make_device):
    sh = make_user("ns", "student")
    th = make_user("nt", "teacher")
    did, tok = make_device(sh, "ndev")
    dsid = _make_dataset(client, sh, did, tok)
    client.post(f"/api/v1/datasets/{dsid}/submit", headers=sh)
    client.post(f"/api/v1/datasets/{dsid}/review", json={"result": "approved"}, headers=th)

    r = client.get("/api/v1/notifications", headers=sh).json()
    assert r["unread"] >= 1 and any(dsid in it["message"] for it in r["items"])

    nid = r["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=sh).status_code == 200
    assert client.get("/api/v1/notifications", headers=sh).json()["unread"] == r["unread"] - 1


def test_read_all(client, make_user):
    h = make_user("nr", "student")
    # 无通知时 read-all 也应成功
    assert client.post("/api/v1/notifications/read-all", headers=h).status_code == 200
