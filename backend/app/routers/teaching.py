"""教学模块路由（异步）：知识点树 / 思考题 / 学生记录。

- 与现有同步路由并存；鉴权复用 deps.get_current_user / require_roles
  （同步依赖，FastAPI 在线程池解析），数据读写走独立 async 引擎（app.teaching）。
- 学生看不到思考题的正确答案（answer 字段对学生隐藏）。
"""
from typing import Any, Optional
import io

from fastapi import APIRouter, Depends, HTTPException, Query, FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import llm, models
from ..deps import get_current_user, require_roles
from ..teaching import (CourseNode, LogKind, Quiz, QuizType, StudentLog,
                        get_session, grade_choice)
from ..teaching_export import TeachingDataExporter

router = APIRouter()


# ---------- 请求体 ----------
class NodeIn(BaseModel):
    title: str
    content: Optional[str] = None
    parent_id: Optional[int] = None
    order_index: int = 0
    course_code: Optional[str] = None


class NodePatch(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    parent_id: Optional[int] = None
    order_index: Optional[int] = None
    course_code: Optional[str] = None


class QuizIn(BaseModel):
    qtype: QuizType
    stem: str
    options: Optional[list] = None
    answer: Optional[Any] = None
    score: float = 1.0


class ReflectionIn(BaseModel):
    content: str
    device_id: Optional[str] = None


class AnswerIn(BaseModel):
    answer: Any = None


# ---------- 序列化 ----------
def _node_dict(n: CourseNode) -> dict:
    return {"id": n.id, "parent_id": n.parent_id, "title": n.title,
            "content": n.content, "order_index": n.order_index, "course_code": n.course_code}


def _quiz_dict(q: Quiz, include_answer: bool) -> dict:
    d = {"id": q.id, "node_id": q.node_id, "qtype": q.qtype.value,
         "stem": q.stem, "options": q.options, "score": q.score}
    if include_answer:
        d["answer"] = q.answer       # 仅教师/管理员可见
    return d


def _is_teacher(user: models.User) -> bool:
    return user.role in ("teacher", "admin")


# ---------- 知识点树 ----------
@router.get("/nodes")
async def list_nodes(course_code: Optional[str] = None,
                     db: AsyncSession = Depends(get_session),
                     user: models.User = Depends(get_current_user)):
    """返回知识点树（一次查询 + Python 组装，避免异步惰性加载/N+1）。"""
    q = select(CourseNode).order_by(CourseNode.order_index, CourseNode.id)
    if course_code:
        q = q.where(CourseNode.course_code == course_code)
    nodes = (await db.execute(q)).scalars().all()
    by_id = {n.id: {**_node_dict(n), "children": []} for n in nodes}
    roots = []
    for n in nodes:
        if n.parent_id and n.parent_id in by_id:
            by_id[n.parent_id]["children"].append(by_id[n.id])
        else:
            roots.append(by_id[n.id])
    return roots


@router.post("/nodes")
async def create_node(body: NodeIn, db: AsyncSession = Depends(get_session),
                      user: models.User = Depends(require_roles("teacher"))):
    if body.parent_id and not await db.get(CourseNode, body.parent_id):
        raise HTTPException(400, "父知识点不存在")
    node = CourseNode(**body.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _node_dict(node)


@router.get("/nodes/{node_id}")
async def get_node(node_id: int, db: AsyncSession = Depends(get_session),
                   user: models.User = Depends(get_current_user)):
    node = await db.get(CourseNode, node_id)
    if not node:
        raise HTTPException(404, "知识点不存在")
    quizzes = (await db.execute(
        select(Quiz).where(Quiz.node_id == node_id).order_by(Quiz.id))).scalars().all()
    return {**_node_dict(node),
            "quizzes": [_quiz_dict(q, _is_teacher(user)) for q in quizzes]}


@router.patch("/nodes/{node_id}")
async def update_node(node_id: int, body: NodePatch,
                      db: AsyncSession = Depends(get_session),
                      user: models.User = Depends(require_roles("teacher"))):
    node = await db.get(CourseNode, node_id)
    if not node:
        raise HTTPException(404, "知识点不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    await db.commit()
    await db.refresh(node)
    return _node_dict(node)


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: int, db: AsyncSession = Depends(get_session),
                      user: models.User = Depends(require_roles("teacher"))):
    node = await db.get(CourseNode, node_id)
    if not node:
        raise HTTPException(404, "知识点不存在")
    await db.delete(node)        # 级联删子树 + 关联思考题/记录
    await db.commit()
    return {"deleted": node_id}


# ---------- 思考题 ----------
@router.post("/nodes/{node_id}/quizzes")
async def add_quiz(node_id: int, body: QuizIn,
                   db: AsyncSession = Depends(get_session),
                   user: models.User = Depends(require_roles("teacher"))):
    if not await db.get(CourseNode, node_id):
        raise HTTPException(404, "知识点不存在")
    quiz = Quiz(node_id=node_id, **body.model_dump())
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    return _quiz_dict(quiz, include_answer=True)


@router.get("/nodes/{node_id}/quizzes")
async def list_quizzes(node_id: int, db: AsyncSession = Depends(get_session),
                       user: models.User = Depends(get_current_user)):
    quizzes = (await db.execute(
        select(Quiz).where(Quiz.node_id == node_id).order_by(Quiz.id))).scalars().all()
    return [_quiz_dict(q, _is_teacher(user)) for q in quizzes]


@router.delete("/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: int, db: AsyncSession = Depends(get_session),
                      user: models.User = Depends(require_roles("teacher"))):
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "题目不存在")
    await db.delete(quiz)
    await db.commit()
    return {"deleted": quiz_id}


# ---------- 学生记录 ----------
@router.post("/nodes/{node_id}/reflection")
async def write_reflection(node_id: int, body: ReflectionIn,
                           db: AsyncSession = Depends(get_session),
                           user: models.User = Depends(get_current_user)):
    if not await db.get(CourseNode, node_id):
        raise HTTPException(404, "知识点不存在")
    log = StudentLog(user_id=user.id, device_id=body.device_id, node_id=node_id,
                     kind=LogKind.reflection, content=body.content)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {"log_id": log.id}


@router.post("/quizzes/{quiz_id}/answer")
async def submit_answer(quiz_id: int, body: AnswerIn,
                        db: AsyncSession = Depends(get_session),
                        user: models.User = Depends(get_current_user)):
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(404, "题目不存在")
    ok, sc = grade_choice(quiz, body.answer)
    content = body.answer if (quiz.qtype == QuizType.short_answer and isinstance(body.answer, str)) else None
    log = StudentLog(user_id=user.id, node_id=quiz.node_id, quiz_id=quiz_id,
                     kind=LogKind.quiz_answer, answer=body.answer,
                     is_correct=ok, score=sc, content=content)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {"log_id": log.id, "is_correct": ok, "score": sc}


@router.get("/logs")
async def list_logs(node_id: Optional[int] = None, student_id: Optional[int] = None,
                    db: AsyncSession = Depends(get_session),
                    user: models.User = Depends(get_current_user)):
    """学生只看自己；教师/管理员可按 student_id / node_id 查全部。"""
    q = select(StudentLog).order_by(StudentLog.created_at.desc())
    if _is_teacher(user):
        if student_id is not None:
            q = q.where(StudentLog.user_id == student_id)
    else:
        q = q.where(StudentLog.user_id == user.id)
    if node_id is not None:
        q = q.where(StudentLog.node_id == node_id)
    logs = (await db.execute(q.limit(500))).scalars().all()
    return [{"id": l.id, "user_id": l.user_id, "node_id": l.node_id, "quiz_id": l.quiz_id,
             "kind": l.kind.value, "content": l.content, "answer": l.answer,
             "is_correct": l.is_correct, "score": l.score,
             "created_at": l.created_at.isoformat() if l.created_at else None}
            for l in logs]


# ---------- AI 助教（疑问答疑 + 学习过程反馈） ----------
class AskIn(BaseModel):
    question: str
    node_id: Optional[int] = None


_SYS = ("你是“众感”平台面向《电气测试技术》《现代检测技术》《能源物联网技术》等课程的 AI 助教。"
        "请用简体中文、面向本科生作答：准确、简洁、鼓励式；涉及实验或数据时给出排查思路与学习建议。")


@router.post("/ai/ask")
async def ai_ask(body: AskIn, db: AsyncSession = Depends(get_session),
                 user: models.User = Depends(get_current_user)):
    """学生疑问答疑：以当前知识点内容为背景，调用 LLM 回答。"""
    node = await db.get(CourseNode, body.node_id) if body.node_id else None
    ctx = f"【当前知识点】{node.title}\n{(node.content or '')[:2000]}\n\n" if node else ""
    try:
        ans = await llm.chat([
            {"role": "system", "content": _SYS},
            {"role": "user", "content": f"{ctx}学生提问：{body.question}"},
        ])
    except Exception:
        ans = None
    if not ans:
        return {"answer": "（AI 助教暂未配置或暂时不可用；教师可在后端 .env 设置 LLM_BASE_URL 后启用。）", "ai": False}
    if node:   # 记录学习过程（关联知识点时）
        db.add(StudentLog(user_id=user.id, node_id=node.id, kind=LogKind.ai_chat,
                          content=body.question, answer={"ai_answer": ans}))
        await db.commit()
    return {"answer": ans, "ai": True}


@router.post("/nodes/{node_id}/ai-feedback")
async def ai_feedback(node_id: int, db: AsyncSession = Depends(get_session),
                      user: models.User = Depends(get_current_user)):
    """学习过程反馈：汇总该生在此知识点的心得与答题，调用 LLM 给出反馈建议。"""
    node = await db.get(CourseNode, node_id)
    if not node:
        raise HTTPException(404, "知识点不存在")
    logs = (await db.execute(select(StudentLog).where(
        StudentLog.user_id == user.id, StudentLog.node_id == node_id))).scalars().all()
    reflections = [l.content for l in logs if l.kind == LogKind.reflection and l.content]
    answered = [l for l in logs if l.kind == LogKind.quiz_answer]
    n_ok = sum(1 for l in answered if l.is_correct)
    summary = (f"知识点：{node.title}\n"
               f"学生心得：{' / '.join(reflections) if reflections else '（暂无）'}\n"
               f"思考题作答：共 {len(answered)} 次，其中正确 {n_ok} 次\n")
    try:
        fb = await llm.chat([
            {"role": "system", "content": _SYS},
            {"role": "user", "content":
                "请基于该生在此知识点的学习记录，给出 150 字以内、鼓励式、可操作的学习反馈与下一步建议：\n" + summary},
        ])
    except Exception:
        fb = None
    if not fb:
        return {"feedback": "（AI 助教暂未配置或暂时不可用。）", "ai": False}
    return {"feedback": fb, "ai": True}


# ========== 数据导出（教师专用） ==========

@router.get("/export-data")
async def export_teaching_data(
    student_id: Optional[int] = None,
    format: str = Query('csv', regex='^(csv|xlsx)$'),
    db: AsyncSession = Depends(get_session),
    user: models.User = Depends(require_roles("teacher"))
):
    """
    导出学生作答数据 + 设备传感器时间序列（仅教师可调用）。

    查询参数：
      - student_id: 学生 ID（可选，不指定则导出所有学生）
      - format: 输出格式（'csv' 或 'xlsx'，默认 'csv'）

    返回：文件下载响应

    示例：
      GET /api/v1/teaching/export-data?format=xlsx
      GET /api/v1/teaching/export-data?student_id=5&format=csv
    """
    exporter = TeachingDataExporter(db)

    try:
        file_bytes, mime_type, filename = await exporter.export_student_logs(
            student_id=student_id,
            format=format
        )
    except Exception as e:
        raise HTTPException(500, f"导出失败：{str(e)}")

    return FileResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        filename=filename,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
