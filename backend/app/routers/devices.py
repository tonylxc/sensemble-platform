from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..security import new_device_token, hash_device_token
from ..schemas import DeviceIn, DeviceRegistered
from ..audit import log
from .. import models

router = APIRouter()


@router.post("", response_model=DeviceRegistered)
def register_device(body: DeviceIn, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    if db.get(models.Device, body.device_id):
        raise HTTPException(400, "设备 ID 已存在")
    token = new_device_token()
    dev = models.Device(device_id=body.device_id, owner_id=user.id, type=body.type,
                        sensors=body.sensors, token_hash=hash_device_token(token), token=token,
                        location=body.location, lat=body.lat, lon=body.lon,
                        sample_interval=body.sample_interval)
    db.add(dev)
    db.commit()
    db.refresh(dev)
    log(db, user.id, "device_register", body.device_id)
    return DeviceRegistered(device_id=dev.device_id, type=dev.type, status=dev.status,
                            last_seen=dev.last_seen, device_token=token)


@router.get("")
def my_devices(all_devices: bool = False, db: Session = Depends(get_db),
               user: models.User = Depends(get_current_user)):
    """列出设备，含在线状态与设备 Token（FR-2.3：超过 3×采样周期未上报判离线）。

    默认仅本人设备；教师/管理员可传 all_devices=true 查看全平台设备（用于可视化/审计）。
    Token 仅对设备拥有者与管理员可见。
    """
    q = select(models.Device)
    if not (all_devices and user.role in ("teacher", "admin")):
        q = q.where(models.Device.owner_id == user.id)
    rows = db.execute(q.order_by(models.Device.created_at.desc())).scalars().all()
    now = datetime.now(timezone.utc)
    out = []
    for d in rows:
        online = bool(d.last_seen and (now - d.last_seen).total_seconds() <= 3 * max(1, d.sample_interval))
        can_see_token = (d.owner_id == user.id or user.role == "admin")
        out.append({"device_id": d.device_id, "type": d.type, "status": d.status,
                    "location": d.location, "sample_interval": d.sample_interval,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "online": online, "owner_id": d.owner_id,
                    "token": d.token if can_see_token else None})
    return out


@router.post("/{device_id}/token/rotate")
def rotate_token(device_id: str, db: Session = Depends(get_db),
                 user: models.User = Depends(get_current_user)):
    """重置（轮换）设备 Token：生成新 Token，旧的立即失效。仅拥有者/管理员。"""
    dev = db.get(models.Device, device_id)
    if not dev or (dev.owner_id != user.id and user.role != "admin"):
        raise HTTPException(404, "设备不存在或无权操作")
    token = new_device_token()
    dev.token = token
    dev.token_hash = hash_device_token(token)
    db.commit()
    log(db, user.id, "device_token_rotate", device_id)
    return {"device_id": device_id, "device_token": token}


@router.delete("/{device_id}")
def deactivate_device(device_id: str, purge: bool = False, db: Session = Depends(get_db),
                      user: models.User = Depends(get_current_user)):
    """停用设备（FR-2.5）。purge=true 时同时清除其历史数据。"""
    dev = db.get(models.Device, device_id)
    if not dev or (dev.owner_id != user.id and user.role != "admin"):
        raise HTTPException(404, "设备不存在或无权操作")
    if purge:
        db.execute(text("DELETE FROM sensor_data WHERE device_id = :d"), {"d": device_id})
    dev.status = "inactive"
    db.commit()
    log(db, user.id, "device_deactivate", device_id, {"purge": purge})
    return {"device_id": device_id, "status": "inactive", "purged": purge}
