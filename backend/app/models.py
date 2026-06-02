from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime, Float, Integer, Text, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="student")
    college: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sensors: Mapped[dict] = mapped_column(JSONB, default=dict)
    token_hash: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_interval: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(16), default="active")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SensorData(Base):
    __tablename__ = "sensor_data"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    device_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Dataset(Base):
    __tablename__ = "datasets"
    dataset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ts_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ts_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dqs: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    tags: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(32), ForeignKey("datasets.dataset_id"))
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    result: Mapped[str] = mapped_column(String(16))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(64), default="default")
    key_hash: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    ntype: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
