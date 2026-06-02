from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import SessionLocal, engine, Base
from .security import hash_password
from .mqtt_ingest import start_mqtt
from . import models
from .routers import auth, devices, data, datasets, internal, keys, open_data, notifications, stats


def ensure_admin():
    db = SessionLocal()
    try:
        exists = db.execute(
            select(models.User).where(models.User.username == settings.admin_username)
        ).scalar_one_or_none()
        if not exists:
            db.add(models.User(username=settings.admin_username,
                               password_hash=hash_password(settings.admin_password),
                               role="admin"))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 表结构由 db/init/001_init.sql 在 DB 首启创建；此处兜底建表（不含 Timescale 超表转换）
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    try:
        ensure_admin()
    except Exception:
        pass
    start_mqtt()
    yield


app = FastAPI(title="众感 Sensemble API", version="1.0-MVP", lifespan=lifespan)

origins = ["*"] if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
app.include_router(internal.router, prefix="/internal/mqtt", tags=["internal"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["api-keys"])
app.include_router(open_data.router, prefix="/api/v1/open", tags=["open-api"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])

# Prometheus 指标（FR-15.2）：暴露 /metrics 供 Prometheus 抓取（依赖缺失时静默跳过）
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=False)
except Exception:
    pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"name": "众感 Sensemble", "version": "1.0-MVP", "docs": "/docs"}
