"""API Key 管理（FR-12.1）：用户为第三方/脚本创建只读访问密钥。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..security import new_api_key, hash_device_token
from ..audit import log
from .. import models

router = APIRouter()


@router.post("")
def create_key(name: str = "default", db: Session = Depends(get_db),
               user: models.User = Depends(get_current_user)):
    plain = new_api_key()
    k = models.ApiKey(owner_id=user.id, name=name[:64], key_hash=hash_device_token(plain))
    db.add(k)
    db.commit()
    db.refresh(k)
    log(db, user.id, "apikey_create", str(k.id))
    return {"id": k.id, "name": k.name, "api_key": plain, "note": "仅此一次显示，请妥善保存"}


@router.get("")
def list_keys(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    rows = db.execute(select(models.ApiKey).where(models.ApiKey.owner_id == user.id)).scalars().all()
    return [{"id": r.id, "name": r.name,
             "created_at": r.created_at.isoformat() if r.created_at else None,
             "last_used": r.last_used.isoformat() if r.last_used else None} for r in rows]


@router.delete("/{key_id}")
def revoke_key(key_id: int, db: Session = Depends(get_db),
               user: models.User = Depends(get_current_user)):
    k = db.get(models.ApiKey, key_id)
    if not k or k.owner_id != user.id:
        raise HTTPException(404, "Key 不存在")
    db.delete(k)
    db.commit()
    log(db, user.id, "apikey_revoke", str(key_id))
    return {"status": "revoked"}
