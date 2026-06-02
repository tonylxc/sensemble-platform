import io
import csv
import datetime as dt


def _time_range():
    end = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)
    start = end - dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _seed_points(client, did, tok, values):
    client.post("/api/v1/data", json=[{"metric": "temperature", "value": v} for v in values],
                headers={"X-Device-Id": did, "X-Device-Token": tok})


def test_full_dataset_lifecycle(client, make_user, make_device):
    sh = make_user("stud", "student")
    th = make_user("teach", "teacher")
    did, tok = make_device(sh, "dloop")
    _seed_points(client, did, tok, [22, 23, 24, 23, 22])
    start, end = _time_range()

    # 创建数据集（自动算 DQS）
    r = client.post("/api/v1/datasets", json={
        "name": "温度集", "device_id": did, "start": start, "end": end,
        "meta": {"sensor_type": "DHT22", "accuracy": "0.5", "sample_interval": 60,
                 "location": "A-301", "calibration_date": "2026-05-30"}}, headers=sh)
    assert r.status_code == 200
    body = r.json()
    dsid = body["dataset_id"]
    assert dsid.startswith("SMDP-") and body["points"] == 5 and body["dqs"] is not None
    assert "citation" in body

    # 提交审核
    assert client.post(f"/api/v1/datasets/{dsid}/submit", headers=sh).status_code == 200

    # 学生无权审核（RBAC 403）
    assert client.post(f"/api/v1/datasets/{dsid}/review", json={"result": "approved"}, headers=sh).status_code == 403

    # 教师审核队列可见
    pend = client.get("/api/v1/datasets/pending", headers=th)
    assert pend.status_code == 200 and any(x["dataset_id"] == dsid for x in pend.json())

    # 教师通过 → 发布
    rv = client.post(f"/api/v1/datasets/{dsid}/review", json={"result": "approved", "comment": "ok"}, headers=th)
    assert rv.status_code == 200 and rv.json()["status"] == "published"

    # 检索可见
    s = client.get("/api/v1/datasets", params={"keyword": "温度"}, headers=th)
    assert any(x["dataset_id"] == dsid for x in s.json())

    # 下载 CSV
    d = client.get(f"/api/v1/datasets/{dsid}/download", params={"format": "csv"}, headers=sh)
    assert d.status_code == 200
    rows = [row for row in csv.reader(io.StringIO(d.text)) if row]
    assert rows[0][:4] == ["ts", "device_id", "metric", "value"]
    assert len(rows) >= 6  # 表头 + 5 个点


def test_reject_flow(client, make_user, make_device):
    sh = make_user("s2", "student")
    th = make_user("t2", "teacher")
    did, tok = make_device(sh, "drej")
    _seed_points(client, did, tok, [1, 2, 3])
    start, end = _time_range()
    dsid = client.post("/api/v1/datasets",
                       json={"name": "待退回", "device_id": did, "start": start, "end": end},
                       headers=sh).json()["dataset_id"]
    client.post(f"/api/v1/datasets/{dsid}/submit", headers=sh)
    rv = client.post(f"/api/v1/datasets/{dsid}/review", json={"result": "rejected", "comment": "元数据缺失"}, headers=th)
    assert rv.json()["status"] == "rejected"


def test_pending_requires_teacher(client, make_user):
    sh = make_user("s3", "student")
    assert client.get("/api/v1/datasets/pending", headers=sh).status_code == 403


def test_private_download_forbidden_for_others(client, make_user, make_device):
    owner = make_user("owner", "student")
    other = make_user("other", "student")
    did, tok = make_device(owner, "dpriv")
    _seed_points(client, did, tok, [10, 11])
    start, end = _time_range()
    dsid = client.post("/api/v1/datasets",
                       json={"name": "私有集", "device_id": did, "start": start, "end": end, "visibility": "private"},
                       headers=owner).json()["dataset_id"]
    # 他人无权下载私有集
    assert client.get(f"/api/v1/datasets/{dsid}/download", headers=other).status_code == 403
