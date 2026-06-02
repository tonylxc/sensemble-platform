import datetime as dt
import hashlib
import secrets

import jwt
from passlib.context import CryptContext

from .config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)


def create_access_token(sub, role: str) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(sub), "role": role, "exp": exp}, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


# 设备 Token：高熵随机串，用 sha256 存储（上报高频，避免 bcrypt 慢校验）
def new_device_token() -> str:
    return secrets.token_urlsafe(32)


def hash_device_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def verify_device_token(t: str, h: str) -> bool:
    return hashlib.sha256(t.encode()).hexdigest() == h


# 对外 API Key（同样高熵 + sha256 存储）
def new_api_key() -> str:
    return "sk_" + secrets.token_urlsafe(32)
