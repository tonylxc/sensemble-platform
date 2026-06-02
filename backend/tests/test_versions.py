import datetime as dt


def _make_dataset(client, h, did, tok, name="版本测试集"):
    client.post("/api/v1/data", json=[{"metric": "temperature", "value": 1}],
                headers={"X-Device-Id": did, "X-Device-Token": tok})
    end = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)).isoformat()
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
    return client.post("/api/v1/datasets",
                       json={"name": name, "device_id": did, "start": start, "end": end,
                             "meta": {"sensor_type": "DHT22"}}, headers=h).json()["dataset_id"]


def test_update_records_versions(client, make_user, make_device):
    h = make_user("ver", "student")
    did, tok = make_device(h, "verdev")
    dsid = _make_dataset(client, h, did, tok)

    r = client.patch(f"/api/v1/datasets/{dsid}",
                     json={"name": "新名字", "meta": {"sensor_type": "SHT30", "accuracy": "0.3"}}, headers=h)
    assert r.status_code == 200 and r.json()["saved_version"] == 1

    client.patch(f"/api/v1/datasets/{dsid}", json={"description": "补充说明"}, headers=h)

    vers = client.get(f"/api/v1/datasets/{dsid}/versions", headers=h).json()
    assert len(vers) == 2 and vers[0]["version"] == 2
    assert any(v["name"] == "版本测试集" for v in vers)   # 最早一版保留了原始名


def test_update_blocks_pii(client, make_user, make_device):
    h = make_user("ver2", "student")
    did, tok = make_device(h, "verdev2")
    dsid = _make_dataset(client, h, did, tok)
    assert client.patch(f"/api/v1/datasets/{dsid}", json={"name": "手机13812345678"}, headers=h).status_code == 400


def test_update_only_editable_when_draft(client, make_user, make_device):
    sh = make_user("ver3", "student")
    th = make_user("ver3t", "teacher")
    did, tok = make_device(sh, "verdev3")
    dsid = _make_dataset(client, sh, did, tok)
    client.post(f"/api/v1/datasets/{dsid}/submit", headers=sh)
    client.post(f"/api/v1/datasets/{dsid}/review", json={"result": "approved"}, headers=th)
    assert client.patch(f"/api/v1/datasets/{dsid}", json={"name": "x"}, headers=sh).status_code == 400
