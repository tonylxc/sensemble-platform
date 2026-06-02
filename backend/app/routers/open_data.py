"""对外开放只读 API（FR-12.1）：第三方用 API Key 访问"已发布且公开"的数据集。

鉴权：请求头 X-API-Key。仅暴露 published + public 数据，保护校内私有数据。
"""
import io
import csv

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_api_key
from .. import models

router = APIRouter()


@router.get("/datasets")
def open_list(keyword: str | None = None, db: Session = Depends(get_db),
              key: models.ApiKey = Depends(get_api_key)):
    q = select(models.Dataset).where(
        models.Dataset.status == "published", models.Dataset.visibility == "public")
    if keyword:
        q = q.where(models.Dataset.name.ilike(f"%{keyword}%"))
    rows = db.execute(q.order_by(models.Dataset.created_at.desc()).limit(200)).scalars().all()
    return [{"dataset_id": d.dataset_id, "name": d.name, "dqs": d.dqs, "grade": d.grade,
             "device_id": d.device_id, "ts_start": d.ts_start.isoformat() if d.ts_start else None,
             "ts_end": d.ts_end.isoformat() if d.ts_end else None,
             "created_at": d.created_at.isoformat() if d.created_at else None} for d in rows]


@router.get("/datasets/{dataset_id}/download")
def open_download(dataset_id: str, format: str = Query("csv", pattern="^(csv|json)$"),
                  db: Session = Depends(get_db), key: models.ApiKey = Depends(get_api_key)):
    ds = db.get(models.Dataset, dataset_id)
    if not ds or ds.status != "published" or ds.visibility != "public":
        raise HTTPException(404, "公开数据集不存在")
    rows = db.execute(select(models.SensorData).where(and_(
        models.SensorData.device_id == ds.device_id,
        models.SensorData.ts >= ds.ts_start,
        models.SensorData.ts <= ds.ts_end)).order_by(models.SensorData.ts.asc())).scalars().all()
    ds.download_count += 1
    db.commit()
    if format == "json":
        return JSONResponse([{"ts": r.ts.isoformat(), "metric": r.metric, "value": r.value} for r in rows])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts", "device_id", "metric", "value", "lat", "lon"])
    for r in rows:
        w.writerow([r.ts.isoformat(), r.device_id, r.metric, r.value, r.lat, r.lon])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={dataset_id}.csv"})
