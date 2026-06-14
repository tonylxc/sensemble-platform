"""教学模块数据模型（异步 SQLAlchemy 2.0）。

独立性保证
- 独立 Base（独立 metadata）：create_all 只建本模块三张表，不碰也不依赖
  现有 users / devices / sensor_data 等同步表。
- 与设备数据"仅逻辑关联"：user_id / device_id 为普通带索引列，**不设外键**指向
  设备侧表；只有教学三表之间（node→quiz→log）才用外键。
- 异步：create_async_engine(asyncpg) + async_sessionmaker + AsyncSession；
  Base 继承 AsyncAttrs，可用 `await obj.awaitable_attrs.children` 安全惰性加载。
  引擎用 NullPool：规避"异步连接绑定到不同事件循环"的坑（如 TestClient 下）。
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (AsyncAttrs, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.pool import NullPool

# 复用现有配置，把同步串转成 asyncpg；独立运行时有兜底
try:
    from .config import settings
    ASYNC_DB_URL = settings.database_url.replace("+psycopg2", "+asyncpg")
except Exception:
    ASYNC_DB_URL = "postgresql+asyncpg://sensemble:sensemble@localhost:5432/sensemble"


class Base(AsyncAttrs, DeclarativeBase):
    """教学模块独立 Base —— 独立 metadata，与设备表互不影响。"""
    pass


class QuizType(str, enum.Enum):
    single = "single"               # 单选
    multiple = "multiple"           # 多选
    short_answer = "short_answer"   # 简答


class LogKind(str, enum.Enum):
    reflection = "reflection"       # 心得体会
    quiz_answer = "quiz_answer"     # 思考题作答


# ---------- 1. 课程知识点（树状上下级） ----------
class CourseNode(Base):
    __tablename__ = "course_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_nodes.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[Optional[str]] = mapped_column(Text)            # 富文本(HTML/Markdown)
    order_index: Mapped[int] = mapped_column(default=0)            # 同级排序
    course_code: Mapped[Optional[str]] = mapped_column(String(64), index=True)  # 归属课程(逻辑)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # 自引用邻接表：parent(多对一) / children(一对多)
    parent: Mapped[Optional["CourseNode"]] = relationship(
        back_populates="children", remote_side="CourseNode.id")
    children: Mapped[list["CourseNode"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan",
        order_by="CourseNode.order_index", lazy="selectin")

    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="node", cascade="all, delete-orphan", lazy="selectin")


# ---------- 2. 思考题（关联知识点） ----------
class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("course_nodes.id", ondelete="CASCADE"), index=True)
    qtype: Mapped[QuizType] = mapped_column(SAEnum(QuizType, native_enum=False, length=20))
    stem: Mapped[str] = mapped_column(Text)                         # 题干
    options: Mapped[Optional[list]] = mapped_column(JSONB)          # [{"key":"A","text":"..."}]
    answer: Mapped[Optional[Any]] = mapped_column(JSONB)            # 单选"A" / 多选["A","C"] / 简答参考
    score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    node: Mapped["CourseNode"] = relationship(back_populates="quizzes")
    logs: Mapped[list["StudentLog"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", lazy="selectin")


# ---------- 3. 学生记录（心得体会 / 作答结果） ----------
class StudentLog(Base):
    __tablename__ = "student_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 逻辑关联：不设外键指向 users/devices，仅存 ID + 索引
    user_id: Mapped[int] = mapped_column(index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    node_id: Mapped[int] = mapped_column(
        ForeignKey("course_nodes.id", ondelete="CASCADE"), index=True)
    quiz_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)

    kind: Mapped[LogKind] = mapped_column(SAEnum(LogKind, native_enum=False, length=20))
    content: Mapped[Optional[str]] = mapped_column(Text)            # 心得体会 / 简答正文
    answer: Mapped[Optional[Any]] = mapped_column(JSONB)            # 选择题作答
    is_correct: Mapped[Optional[bool]] = mapped_column()            # 自动判分(简答为 None)
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    node: Mapped["CourseNode"] = relationship()
    quiz: Mapped[Optional["Quiz"]] = relationship(back_populates="logs")


# 复合索引：高频"按学生查某知识点记录"
Index("ix_studentlog_user_node", StudentLog.user_id, StudentLog.node_id)


# ---------- 选择题自动判分 ----------
def grade_choice(quiz: Quiz, submitted: Any) -> tuple[Optional[bool], float]:
    """返回 (是否正确, 得分)。简答返回 (None, 0.0)，交人工或关键词另判。"""
    if quiz.qtype == QuizType.short_answer:
        return None, 0.0
    if quiz.qtype == QuizType.single:
        ok = submitted == quiz.answer
    else:  # multiple：无序集合比较
        ok = set(submitted or []) == set(quiz.answer or [])
    return ok, (quiz.score if ok else 0.0)


# ---------- 异步引擎 / 会话 / 建表 ----------
engine = create_async_engine(ASYNC_DB_URL, poolclass=NullPool, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：async with 自动管理连接。"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_teaching_models() -> None:
    """只建本模块三张表（独立 metadata，不影响设备表）。在 lifespan 启动时 await 调用。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
