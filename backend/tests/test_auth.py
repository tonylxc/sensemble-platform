def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json={"username": "alice", "password": "pw", "role": "student"})
    assert r.status_code == 200
    assert r.json()["role"] == "student" and r.json()["access_token"]

    # 重复注册
    assert client.post("/api/v1/auth/register", json={"username": "alice", "password": "pw"}).status_code == 400

    # 登录（表单）
    r3 = client.post("/api/v1/auth/login", data={"username": "alice", "password": "pw"})
    assert r3.status_code == 200
    token = r3.json()["access_token"]

    # /me
    r4 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 200 and r4.json()["username"] == "alice"


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={"username": "bob", "password": "pw"})
    assert client.post("/api/v1/auth/login", data={"username": "bob", "password": "WRONG"}).status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_register_role_defaults_to_student(client):
    # 非法/越权角色应回落到 student（不能自助注册 admin）
    r = client.post("/api/v1/auth/register", json={"username": "evil", "password": "pw", "role": "admin"})
    assert r.json()["role"] == "student"
