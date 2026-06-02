from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import hash_password, verify_password, create_access_token
from ..schemas import RegisterIn, Token, UserOut
from ..deps import get_current_user
from ..audit import log
from .. import models

router = APIRouter()


@router.post("/register", response_model=Token)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.execute(select(models.User).where(models.User.username == body.username)).scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    role = body.role if body.role in ("student", "teacher") else "student"
    u = models.User(username=body.username, email=body.email,
                    password_hash=hash_password(body.password), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    log(db, u.id, "register", u.username)
    return Token(access_token=create_access_token(u.id, u.role), role=u.role)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.execute(select(models.User).where(models.User.username == form.username)).scalar_one_or_none()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    log(db, u.id, "login", u.username)
    return Token(access_token=create_access_token(u.id, u.role), role=u.role)


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
