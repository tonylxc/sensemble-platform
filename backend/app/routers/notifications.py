"""站内通知（FR-13.1）：查看 / 标记已读。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from .. import models

router = APIRouter()


@router.get("")
def my_notifications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.execute(
        select(models.Notification).where(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc()).limit(100)
    ).scalars().all()
    unread = db.scalar(
        select(func.count()).select_from(models.Notification)
        .where(models.Notification.user_id == user.id, models.Notification.is_read.is_(False))
    ) or 0
    return {"unread": unread, "items": [
        {"id": n.id, "type": n.ntype, "message": n.message, "link": n.link,
         "is_read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None}
        for n in rows]}


@router.post("/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = db.get(models.Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "通知不存在")
    n.is_read = True
    db.commit()
    return {"status": "ok"}


@router.post("/read-all")
def mark_all(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.execute(update(models.Notification)
               .where(models.Notification.user_id == user.id, models.Notification.is_read.is_(False))
               .values(is_read=True))
    db.commit()
    return {"status": "ok"}
