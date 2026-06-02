import io
import csv
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, text, and_, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..schemas import DatasetIn, ReviewIn
from ..audit import log
from ..dqs import compute_full
from ..pii import scan_text
from ..notify import notify
from .. import models

router = APIRouter()


def _new_id(db: Session) -> str:
    seq = db.execute(text("SELECT nextval('dataset_seq')")).scalar()
    return f"SMDP-{datetime.now().year}-{int(seq):04d}"


def _citation(author: str, name: str, did: str) -> str:
    return f"{author}. {name} [Sensemble]. {datetime.now().year}. {did}."


@router.post("")
def create_dataset(body: DatasetIn, db: Session = Depends(get_db),
                   user: models.User = Depends(get_current_user)):
    """按 设备+时间范围 打包数据集，自动计算 DQS（FR-8.1 / FR-6.1）。"""
    # PII / 敏感信息预检（FR-9.2 / FR-10.2）
    pii_hits = scan_text(body.name, body.description or "", str(body.meta))
    if pii_hits:
        raise HTTPException(400, "检测到疑似敏感/隐私信息：" + "、".join(pii_hits) + "；请删除后再提交")
    rows = db.execute(select(models.SensorData).where(and_(
        models.SensorData.device_id == body.device_id,
        models.SensorData.ts >= body.start,
        models.SensorData.ts <= body.end))).scalars().all()
    values = [r.value for r in rows if r.value is not None]
    dev = db.get(models.Device, body.device_id)
    interval = dev.sample_interval if dev else 60
    expected = max(1, int((body.end - body.start).total_seconds() / max(1, interval)))
    timestamps = [r.ts for r in rows]
    score, grade, detail = compute_full(len(rows), expected, body.meta, values, timestamps, interval)

    did = _new_id(db)
    ds = models.Dataset(
        dataset_id=did, name=body.name, creator_id=user.id, description=body.description,
        meta={**body.meta, "dqs_detail": detail}, device_id=body.device_id,
        ts_start=body.start, ts_end=body.end, dqs=score, grade=grade,
        visibility=body.visibility if body.visibility in ("public", "private") else "private",
        status="draft", tags=body.tags)
    db.add(ds)
    db.commit()
    log(db, user.id, "dataset_create", did, {"dqs": score})
    return {"dataset_id": did, "dqs": score, "grade": grade, "status": "draft",
            "points": len(rows), "citation": _citation(user.username, body.name, did)}


@router.post("/{dataset_id}/submit")
def submit(dataset_id: str, db: Session = Depends(get_db),
           user: models.User = Depends(get_current_user)):
    ds = db.get(models.Dataset, dataset_id)
    if not ds or ds.creator_id != user.id:
        raise HTTPException(404, "数据集不存在或非本人")
    if ds.status not in ("draft", "rejected"):
        raise HTTPException(400, f"当前状态 {ds.status} 不可提交")
    ds.status = "pending"
    db.commit()
    log(db, user.id, "dataset_submit", dataset_id)
    return {"dataset_id": dataset_id, "status": "pending"}


@router.post("/{dataset_id}/review")
def review(dataset_id: str, body: ReviewIn, db: Session = Depends(get_db),
           user: models.User = Depends(require_roles("teacher"))):
    ds = db.get(models.Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "数据集不存在")
    if body.result not in ("approved", "rejected"):
        raise HTTPException(400, "result 必须为 approved/rejected")
    ds.status = "published" if body.result == "approved" else "rejected"
    db.add(models.Review(dataset_id=dataset_id, reviewer_id=user.id,
                         result=body.result, comment=body.comment))
    db.commit()
    log(db, user.id, "dataset_review", dataset_id, {"result": body.result})
    msg = (f"数据集 {dataset_id}（{ds.name}）审核"
           + ("通过并已发布" if body.result == "approved" else "被退回")
           + (f"：{body.comment}" if body.comment else ""))
    notify(db, ds.creator_id, "review", msg, link="/datasets")
    return {"dataset_id": dataset_id, "status": ds.status}


@router.get("")
def search(keyword: Optional[str] = None, sort: str = "time",
           db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """检索：公开集 + 本人集（FR-11.1）。"""
    q = select(models.Dataset).where(
        or_(models.Dataset.status == "published", models.Dataset.creator_id == user.id))
    if keyword:
        like = f"%{keyword}%"
        q = q.where(or_(models.Dataset.name.ilike(like), models.Dataset.description.ilike(like)))
    order = {"dqs": models.Dataset.dqs.desc(),
             "downloads": models.Dataset.download_count.desc(),
             "time": models.Dataset.created_at.desc()}.get(sort, models.Dataset.created_at.desc())
    rows = db.execute(q.order_by(order).limit(200)).scalars().all()
    return [{"dataset_id": d.dataset_id, "name": d.name, "dqs": d.dqs, "grade": d.grade,
             "status": d.status, "visibility": d.visibility, "downloads": d.download_count,
             "created_at": d.created_at.isoformat() if d.created_at else None} for d in rows]


@router.get("/pending")
def pending(db: Session = Depends(get_db), user: models.User = Depends(require_roles("teacher"))):
    """审核队列：所有待审数据集（教师/管理员，FR-10.1）。"""
    rows = db.execute(select(models.Dataset).where(models.Dataset.status == "pending")
                      .order_by(models.Dataset.created_at.asc())).scalars().all()
    return [{"dataset_id": d.dataset_id, "name": d.name, "creator_id": d.creator_id,
             "dqs": d.dqs, "grade": d.grade, "device_id": d.device_id,
             "created_at": d.created_at.isoformat() if d.created_at else None} for d in rows]


@router.get("/{dataset_id}/download")
def download(dataset_id: str, format: str = Query("csv", pattern="^(csv|json)$"),
             db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    ds = db.get(models.Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "数据集不存在")
    if ds.visibility != "public" and ds.creator_id != user.id and user.role not in ("teacher", "admin"):
        raise HTTPException(403, "无权下载该数据集")
    rows = db.execute(select(models.SensorData).where(and_(
        models.SensorData.device_id == ds.device_id,
        models.SensorData.ts >= ds.ts_start,
        models.SensorData.ts <= ds.ts_end)).order_by(models.SensorData.ts.asc())).scalars().all()
    ds.download_count += 1
    db.commit()
    log(db, user.id, "dataset_download", dataset_id)

    if format == "json":
        return JSONResponse([{"ts": r.ts.isoformat(), "metric": r.metric, "value": r.value}
                             for r in rows])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ts", "device_id", "metric", "value", "lat", "lon"])
    for r in rows:
        w.writerow([r.ts.isoformat(), r.device_id, r.metric, r.value, r.lat, r.lon])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={dataset_id}.csv"})
