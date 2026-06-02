import datetime as dt
from app.pii import scan_text


def test_scan_detects_pii():
    assert "疑似手机号" in scan_text("联系方式 13812345678")
    assert "疑似身份证号" in scan_text("身份 11010119900307123X")
    assert "疑似邮箱地址" in scan_text("发到 a.b@example.com")
    assert any("敏感词" in x for x in scan_text("包含人脸图像"))


def test_scan_clean_text_passes():
    assert scan_text("教学楼A301温湿度一周监测", "DHT22 采集") == []


def test_dataset_create_blocks_pii(client, make_user, make_device):
    h = make_user("piiu", "student")
    did, tok = make_device(h, "piidev")
    client.post("/api/v1/data", json=[{"metric": "temperature", "value": 1}],
                headers={"X-Device-Id": did, "X-Device-Token": tok})
    end = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1)).isoformat()
    start = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat()
    r = client.post("/api/v1/datasets",
                    json={"name": "学生手机13812345678温度", "device_id": did, "start": start, "end": end},
                    headers=h)
    assert r.status_code == 400 and "敏感" in r.json()["detail"]
