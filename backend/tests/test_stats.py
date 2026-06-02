def test_stats_requires_teacher(client, make_user):
    sh = make_user("ss", "student")
    assert client.get("/api/v1/stats/overview", headers=sh).status_code == 403


def test_stats_overview(client, make_user):
    th = make_user("ts", "teacher")
    r = client.get("/api/v1/stats/overview", headers=th)
    assert r.status_code == 200
    j = r.json()
    assert {"users", "devices", "data_points", "datasets", "downloads"} <= set(j)
    assert j["users"] >= 1 and "by_status" in j["datasets"]
