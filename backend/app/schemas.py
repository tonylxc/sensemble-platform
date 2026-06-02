from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "student"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    college: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceIn(BaseModel):
    device_id: str
    type: Optional[str] = None
    sensors: dict = {}
    location: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    sample_interval: int = 60


class DeviceOut(BaseModel):
    device_id: str
    type: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceRegistered(DeviceOut):
    device_token: str  # 仅注册时返回一次，请妥善保存


class DataPoint(BaseModel):
    metric: str
    value: float
    device_ts: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class DatasetIn(BaseModel):
    name: str
    device_id: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    meta: dict = {}
    tags: list[str] = []
    visibility: str = "private"  # public / private


class ReviewIn(BaseModel):
    result: str  # approved / rejected
    comment: Optional[str] = None
