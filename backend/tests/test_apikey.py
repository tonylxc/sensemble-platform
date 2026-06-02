def test_create_and_use_api_key(client, make_user):
    h = make_user("apiu", "teacher")

    # 创建 key
    r = client.post("/api/v1/keys", params={"name": "k1"}, headers=h)
    assert r.status_code == 200
    key = r.json()["api_key"]
    assert key.startswith("sk_")

    # 列出 key
    assert any(k["name"] == "k1" for k in client.get("/api/v1/keys", headers=h).json())

    # 开放接口：无 key → 401
    assert client.get("/api/v1/open/datasets").status_code == 401
    # 错误 key → 401
    assert client.get("/api/v1/open/datasets", headers={"X-API-Key": "sk_wrong"}).status_code == 401
    # 正确 key → 200（列表可空）
    r2 = client.get("/api/v1/open/datasets", headers={"X-API-Key": key})
    assert r2.status_code == 200 and isinstance(r2.json(), list)


def test_revoke_api_key(client, make_user):
    h = make_user("apiu2", "student")
    kid = client.post("/api/v1/keys", headers=h).json()["id"]
    key = None
    # 撤销
    assert client.delete(f"/api/v1/keys/{kid}", headers=h).status_code == 200
    assert client.get("/api/v1/keys", headers=h).json() == []
