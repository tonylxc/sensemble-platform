"""EMQX 认证/授权回调（一机一 Token，FR-2.2/3.2）。

EMQX 在设备 CONNECT 时调用 /auth，在 PUB/SUB 时调用 /acl。
- 设备：username=device_id，password=设备 Token → 校验 token_hash。
- 后端 ingest：用服务账号登录并标记 is_superuser（可订阅通配主题、绕过 ACL）。
这些接口不走 JWT；可选用共享密钥头 x-emqx-secret 限制只有 EMQX 能调用。
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..security import verify_device_token
from .. import models

router = APIRouter()


def _secret_ok(secret: str | None) -> bool:
    return (not settings.mqtt_auth_secret) or (secret == settings.mqtt_auth_secret)


@router.post("/auth")
def mqtt_auth(body: dict, db: Session = Depends(get_db),
              x_emqx_secret: str = Header(None, alias="x-emqx-secret")):
    if not _secret_ok(x_emqx_secret):
        return {"result": "deny"}
    u = body.get("username")
    p = body.get("password")
    # 后端 ingest 服务账号 → 超级用户（订阅通配、绕过 ACL）
    if u and u == settings.mqtt_backend_user and p == settings.mqtt_backend_password:
        return {"result": "allow", "is_superuser": True}
    if not u or not p:
        return {"result": "deny"}
    dev = db.get(models.Device, u)
    if dev and dev.status == "active" and verify_device_token(p, dev.token_hash):
        return {"result": "allow", "is_superuser": False}
    return {"result": "deny"}


@router.post("/acl")
def mqtt_acl(body: dict, x_emqx_secret: str = Header(None, alias="x-emqx-secret")):
    if not _secret_ok(x_emqx_secret):
        return {"result": "deny"}
    u = body.get("username") or ""
    topic = body.get("topic") or ""
    # 设备仅能访问自身主题树：sensemble/{device_id}/#
    if u and topic.startswith(f"sensemble/{u}/"):
        return {"result": "allow"}
    return {"result": "deny"}
