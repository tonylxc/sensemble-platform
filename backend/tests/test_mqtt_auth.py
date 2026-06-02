from app.config import settings


def test_auth_allows_valid_device(client, make_user, make_device):
    h = make_user("mq_u1")
    did, tok = make_device(h, "mq-dev-1")
    r = client.post("/internal/mqtt/auth", json={"username": did, "password": tok})
    assert r.status_code == 200 and r.json()["result"] == "allow"
    assert r.json().get("is_superuser") is False


def test_auth_denies_bad_token(client, make_user, make_device):
    h = make_user("mq_u2")
    did, _ = make_device(h, "mq-dev-2")
    r = client.post("/internal/mqtt/auth", json={"username": did, "password": "WRONG"})
    assert r.json()["result"] == "deny"


def test_auth_denies_unknown_device(client):
    r = client.post("/internal/mqtt/auth", json={"username": "ghost", "password": "x"})
    assert r.json()["result"] == "deny"


def test_auth_backend_superuser(client):
    r = client.post("/internal/mqtt/auth",
                    json={"username": settings.mqtt_backend_user, "password": settings.mqtt_backend_password})
    body = r.json()
    assert body["result"] == "allow" and body["is_superuser"] is True


def test_acl_allows_own_topic(client, make_user, make_device):
    h = make_user("mq_u3")
    did, _ = make_device(h, "mq-dev-3")
    ok = client.post("/internal/mqtt/acl",
                     json={"username": did, "topic": f"sensemble/{did}/data", "action": "publish"})
    assert ok.json()["result"] == "allow"


def test_acl_denies_other_topic(client, make_user, make_device):
    h = make_user("mq_u4")
    did, _ = make_device(h, "mq-dev-4")
    bad = client.post("/internal/mqtt/acl",
                      json={"username": did, "topic": "sensemble/someone-else/data", "action": "publish"})
    assert bad.json()["result"] == "deny"
