from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, and_, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_device, get_current_user
from ..schemas import DataPoint
from ..idw import interpolate
from ..ratelimit import check_rate
from ..config import settings
from .. import models

router = APIRouter()


@router.post("")
def ingest(points: list[DataPoint], db: Session = Depends(get_db),
           dev: models.Device = Depends(get_device)):
    """HTTP 上报（FR-3.1）。Header: X-Device-Id / X-Device-Token。"""
    if not check_rate(dev.device_id, settings.rate_limit_min_interval):
        raise HTTPException(429, "上报过于频繁，请降低频率（限流）")
    now = datetime.now(timezone.utc)
    for p in points:
        db.add(models.SensorData(
            device_id=dev.device_id, ts=now, device_ts=p.device_ts,
            metric=p.metric, value=p.value,
            lat=p.lat if p.lat is not None else dev.lat,
            lon=p.lon if p.lon is not None else dev.lon,
            raw=p.model_dump(mode="json")))
    dev.last_seen = now
    dev.offline_alerted = False   # 重新上报 → 清除离线告警标记
    db.commit()
    return {"status": "success", "received": len(points)}


@router.get("")
def query(device_id: str, metric: Optional[str] = None,
          start: Optional[datetime] = None, end: Optional[datetime] = None,
          limit: int = Query(20000, le=50000),
          db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """时序查询（FR-4.1）。"""
    conds = [models.SensorData.device_id == device_id]
    if metric:
        conds.append(models.SensorData.metric == metric)
    if start:
        conds.append(models.SensorData.ts >= start)
    if end:
        conds.append(models.SensorData.ts <= end)
    rows = db.execute(
        select(models.SensorData).where(and_(*conds))
        .order_by(models.SensorData.ts.asc()).limit(limit)
    ).scalars().all()
    return [{"ts": r.ts.isoformat(), "metric": r.metric, "value": r.value,
             "lat": r.lat, "lon": r.lon} for r in rows]


@router.get("/heatmap")
def heatmap(metric: str = "temperature", db: Session = Depends(get_db),
            user: models.User = Depends(get_current_user)):
    """空间热力图（FR-7.2/7.3）：取每个设备该指标的最新值，做 IDW 插值返回网格。"""
    rows = db.execute(text("""
        SELECT DISTINCT ON (sd.device_id) sd.device_id AS device_id, sd.value AS value,
               COALESCE(sd.lat, d.lat) AS lat, COALESCE(sd.lon, d.lon) AS lon
        FROM sensor_data sd JOIN devices d ON d.device_id = sd.device_id
        WHERE sd.metric = :m AND sd.value IS NOT NULL
          AND COALESCE(sd.lat, d.lat) IS NOT NULL AND COALESCE(sd.lon, d.lon) IS NOT NULL
        ORDER BY sd.device_id, sd.ts DESC
    """), {"m": metric}).mappings().all()
    points = [{"device_id": r["device_id"], "value": float(r["value"]),
               "lat": float(r["lat"]), "lon": float(r["lon"])} for r in rows]
    if not points:
        return {"metric": metric, "grid": None}
    return {"metric": metric, "grid": interpolate(points)}
