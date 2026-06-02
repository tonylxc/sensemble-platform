from sqlalchemy import text
from app.database import SessionLocal
from app.monitor import check_offline


def _make_stale(engine, did):
    with engine.begin() as conn:
        conn.execute(text("UPDATE devices SET last_seen = now() - interval '1 hour', "
                          "offline_alerted = false WHERE device_id = :d"), {"d": did})


def test_offline_alert_created(client, make_user, make_device, engine):
    h = make_user("mon", "student")
    did, tok = make_device(h, "mondev")   # sample_interval=60 → 3×=180s
    client.post("/api/v1/data", json=[{"metric": "t", "value": 1}],
                headers={"X-Device-Id": did, "X-Device-Token": tok})
    _make_stale(engine, did)
    db = SessionLocal()
    try:
        n = check_offline(db)
    finally:
        db.close()
    assert n >= 1
    msgs = [it["message"] for it in client.get("/api/v1/notifications", headers=h).json()["items"]]
    assert any("离线" in m for m in msgs)


def test_offline_alert_not_duplicated(client, make_user, make_device, engine):
    h = make_user("mon2", "student")
    did, tok = make_device(h, "mondev2")
    client.post("/api/v1/data", json=[{"metric": "t", "value": 1}],
                headers={"X-Device-Id": did, "X-Device-Token": tok})
    _make_stale(engine, did)
    db = SessionLocal()
    try:
        first = check_offline(db)
        second = check_offline(db)   # 已告警过 → 不再重复
    finally:
        db.close()
    assert first >= 1 and second == 0
