"""设备离线主动告警（FR-2.3）：定时巡检，对刚离线的设备给拥有者发站内通知。"""
import threading
import time
import datetime as dt

from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .notify import notify
from . import models


def check_offline(db) -> int:
    """单次巡检：对 超过 3×采样周期 未上报、且未告警过 的活跃设备发通知。返回新增告警数。"""
    now = dt.datetime.now(dt.timezone.utc)
    devs = db.execute(select(models.Device).where(
        models.Device.status == "active",
        models.Device.offline_alerted.is_(False),
        models.Device.last_seen.is_not(None),
    )).scalars().all()
    n = 0
    for d in devs:
        if (now - d.last_seen).total_seconds() > 3 * max(1, d.sample_interval):
            notify(db, d.owner_id, "device_offline",
                   f"设备 {d.device_id} 已离线（超过 {3 * d.sample_interval}s 未上报）", link="/devices")
            d.offline_alerted = True
            n += 1
    if n:
        db.commit()
    return n


def start_offline_monitor():
    if not settings.offline_monitor_enabled:
        return

    def run():
        while True:
            time.sleep(max(10, settings.offline_check_interval))
            db = SessionLocal()
            try:
                check_offline(db)
            except Exception:
                db.rollback()
            finally:
                db.close()

    threading.Thread(target=run, daemon=True).start()
