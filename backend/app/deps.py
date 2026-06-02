from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_access_token, verify_device_token, hash_device_token
from . import models

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> models.User:
    if not token:
        raise HTTPException(401, "未登录")
    try:
        payload = decode_access_token(token)
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "无效或过期的令牌")
    user = db.get(models.User, uid)
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


def require_roles(*roles: str):
    """admin 始终放行；其余按角色白名单。"""
    def _dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != "admin" and user.role not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return _dep


def get_device(
    x_device_id: str = Header(None, alias="X-Device-Id"),
    x_device_token: str = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db),
) -> models.Device:
    if not x_device_id or not x_device_token:
        raise HTTPException(401, "缺少设备凭据 (X-Device-Id / X-Device-Token)")
    dev = db.get(models.Device, x_device_id)
    if not dev or not verify_device_token(x_device_token, dev.token_hash):
        raise HTTPException(401, "设备 Token 无效")
    return dev


def get_api_key(x_api_key: str = Header(None, alias="X-API-Key"),
                db: Session = Depends(get_db)) -> models.ApiKey:
    """对外开放接口鉴权（FR-12.1）：Header X-API-Key。"""
    if not x_api_key:
        raise HTTPException(401, "缺少 API Key（请求头 X-API-Key）")
    row = db.execute(
        select(models.ApiKey).where(models.ApiKey.key_hash == hash_device_token(x_api_key))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(401, "无效的 API Key")
    row.last_used = datetime.now(timezone.utc)
    db.commit()
    return row
