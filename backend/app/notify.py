"""站内通知助手（FR-13.1）。"""
from sqlalchemy.orm import Session
from . import models


def notify(db: Session, user_id: int, ntype: str, message: str, link: str | None = None):
    db.add(models.Notification(user_id=user_id, ntype=ntype, message=message, link=link))
    db.commit()
