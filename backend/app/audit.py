"""审计日志助手（安全底线，FR-16.1）。"""
from sqlalchemy.orm import Session
from . import models


def log(db: Session, actor_id, action: str, target: str | None = None, detail: dict | None = None):
    db.add(models.AuditLog(actor_id=actor_id, action=action, target=target, detail=detail))
    db.commit()
