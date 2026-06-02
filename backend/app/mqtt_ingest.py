"""MQTT 接入（FR-3.2）：订阅 sensemble/+/data，解析后写入时序库。

后台线程随应用启动。设备身份：topic 中的 deviceId + payload 内可选 token 兜底校验；
生产环境应在 EMQX 侧配置认证/ACL（一机一 Token），此处为 MVP 兜底。

支持的报文：
  单点：{"token":"...", "metric":"temperature", "value":23.5, "device_ts":"..."}
  多点：{"token":"...", "data":[{"metric":"temperature","value":23.5}, {"metric":"humidity","value":45}]}
"""
import json
import threading
import time
import datetime as dt

import paho.mqtt.client as mqtt

from .config import settings
from .database import SessionLocal
from .security import verify_device_token
from . import models


def _handle(topic: str, payload: bytes):
    try:
        device_id = topic.split("/")[1]
        body = json.loads(payload.decode("utf-8"))
    except Exception:
        return
    db = SessionLocal()
    try:
        dev = db.get(models.Device, device_id)
        if not dev:
            return
        token = body.get("token")
        if token and not verify_device_token(token, dev.token_hash):
            return  # 鉴权失败丢弃
        points = body.get("data") or body.get("points") or []
        if isinstance(body.get("metric"), str):
            points = [{"metric": body["metric"], "value": body.get("value"),
                       "device_ts": body.get("device_ts")}]
        now = dt.datetime.now(dt.timezone.utc)
        for p in points:
            db.add(models.SensorData(
                device_id=device_id, ts=now, device_ts=p.get("device_ts"),
                metric=p["metric"], value=p.get("value"),
                lat=p.get("lat", dev.lat), lon=p.get("lon", dev.lon), raw=p))
        dev.last_seen = now
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _on_connect(client, userdata, flags, reason_code, properties=None):
    client.subscribe(settings.mqtt_topic)


def _on_message(client, userdata, msg):
    _handle(msg.topic, msg.payload)


def start_mqtt():
    if not settings.mqtt_enabled:
        return

    def run():
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        # 用服务账号登录 EMQX（认证回调里识别为超级用户，可订阅通配主题）
        client.username_pw_set(settings.mqtt_backend_user, settings.mqtt_backend_password)
        client.on_connect = _on_connect
        client.on_message = _on_message
        while True:
            try:
                client.connect(settings.mqtt_host, settings.mqtt_port, 60)
                client.loop_forever()
            except Exception:
                time.sleep(5)

    threading.Thread(target=run, daemon=True).start()
