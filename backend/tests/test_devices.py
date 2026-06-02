def test_register_device_returns_token(client, make_user):
    h = make_user("stu1")
    r = client.post("/api/v1/devices", json={"device_id": "d1", "type": "ESP32"}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["device_id"] == "d1" and body["device_token"]

    lst = client.get("/api/v1/devices", headers=h)
    assert lst.status_code == 200 and any(d["device_id"] == "d1" for d in lst.json())


def test_device_requires_auth(client):
    assert client.post("/api/v1/devices", json={"device_id": "d2"}).status_code == 401


def test_duplicate_device_id(client, make_user):
    h = make_user("stu2")
    client.post("/api/v1/devices", json={"device_id": "dup"}, headers=h)
    assert client.post("/api/v1/devices", json={"device_id": "dup"}, headers=h).status_code == 400


def test_device_list_has_online_flag(client, make_user):
    h = make_user("stu5")
    client.post("/api/v1/devices", json={"device_id": "d5"}, headers=h)
    dev = next(d for d in client.get("/api/v1/devices", headers=h).json() if d["device_id"] == "d5")
    assert "online" in dev and dev["online"] is False   # 从未上报 → 离线


def test_deactivate_device(client, make_user):
    h = make_user("stu6")
    client.post("/api/v1/devices", json={"device_id": "d6"}, headers=h)
    r = client.delete("/api/v1/devices/d6", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "inactive"
    dev = next(d for d in client.get("/api/v1/devices", headers=h).json() if d["device_id"] == "d6")
    assert dev["status"] == "inactive"
