"""运营统计（FR-14.1）：教师/管理员查看平台 KPI。"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from .. import models

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: models.User = Depends(require_roles("teacher"))):
    def cnt(model):
        return db.scalar(select(func.count()).select_from(model)) or 0

    by_status = dict(db.execute(
        select(models.Dataset.status, func.count()).group_by(models.Dataset.status)).all())
    grade_dist = dict(db.execute(
        select(models.Dataset.grade, func.count())
        .where(models.Dataset.status == "published").group_by(models.Dataset.grade)).all())
    downloads = db.scalar(select(func.coalesce(func.sum(models.Dataset.download_count), 0))) or 0

    return {
        "users": cnt(models.User),
        "devices": cnt(models.Device),
        "data_points": cnt(models.SensorData),
        "datasets": {"total": cnt(models.Dataset), "by_status": by_status},
        "downloads": downloads,
        "grade_distribution": {(g or "-"): c for g, c in grade_dist.items()},
    }
