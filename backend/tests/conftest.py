"""pytest 公共夹具：连接测试库、建表、每个用例前清库。

测试库连接由环境变量提供（CI 注入 / 本地可 export）：
  DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME  (默认 localhost:5432 / sensemble / sensemble_test)
"""
import os

os.environ.setdefault("MQTT_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "sensemble")
os.environ.setdefault("DB_PASSWORD", "sensemble")
os.environ.setdefault("DB_NAME", "sensemble_test")

import pytest

TABLES = "users, devices, sensor_data, datasets, reviews, audit_logs, api_keys, notifications"


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy import text
    from app.database import engine as _engine, Base
    from app import models  # noqa: F401  注册 ORM 模型
    Base.metadata.create_all(bind=_engine)
    with _engine.begin() as conn:
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS dataset_seq START 1"))
    return _engine


@pytest.fixture(scope="session")
def client(engine):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean(engine):
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
        conn.execute(text("ALTER SEQUENCE dataset_seq RESTART WITH 1"))
    yield


@pytest.fixture
def make_user(client):
    """注册并登录一个用户，返回鉴权头。"""
    def _make(username, role="student", password="pw"):
        client.post("/api/v1/auth/register", json={"username": username, "password": password, "role": role})
        r = client.post("/api/v1/auth/login", data={"username": username, "password": password})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _make


@pytest.fixture
def make_device(client):
    """为某用户注册设备，返回 (device_id, device_token)。"""
    def _make(headers, device_id="dev1", sample_interval=60):
        r = client.post("/api/v1/devices",
                        json={"device_id": device_id, "type": "ESP32", "sample_interval": sample_interval},
                        headers=headers)
        return device_id, r.json()["device_token"]
    return _make
