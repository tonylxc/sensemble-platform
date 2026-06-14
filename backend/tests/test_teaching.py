"""教学模块端到端测试（异步路由经 TestClient 同步调用）。

依赖 client 夹具触发 lifespan → init_teaching_models() 建表。
教学表与设备表独立，clean 夹具不 TRUNCATE 它们；本测试用创建出的 ID 自洽断言。
"""


def test_teaching_flow(client, make_user):
    teacher = make_user("t_teach", role="teacher")
    student = make_user("s_stud", role="student")

    # 1) 建知识点（树）
    r = client.post("/api/v1/teaching/nodes",
                    json={"title": "第1章 传感器原理", "content": "<p>导论</p>", "course_code": "EE101T"},
                    headers=teacher)
    assert r.status_code == 200, r.text
    node_id = r.json()["id"]
    r = client.post("/api/v1/teaching/nodes",
                    json={"title": "1.1 热电效应", "parent_id": node_id, "course_code": "EE101T"},
                    headers=teacher)
    child_id = r.json()["id"]

    # 树状返回：子节点挂在父下
    r = client.get("/api/v1/teaching/nodes?course_code=EE101T", headers=student)
    assert r.status_code == 200
    root = next(n for n in r.json() if n["id"] == node_id)
    assert any(c["id"] == child_id for c in root["children"])

    # 学生无权建知识点
    assert client.post("/api/v1/teaching/nodes", json={"title": "x"}, headers=student).status_code == 403

    # 2) 加单选思考题（答案 B，2 分）
    r = client.post(f"/api/v1/teaching/nodes/{node_id}/quizzes",
                    json={"qtype": "single", "stem": "热电偶基于哪种效应？",
                          "options": [{"key": "A", "text": "光电"}, {"key": "B", "text": "塞贝克"}],
                          "answer": "B", "score": 2},
                    headers=teacher)
    assert r.status_code == 200, r.text
    quiz_id = r.json()["id"]

    # 3) 学生看题不含答案；教师看题含答案
    sq = client.get(f"/api/v1/teaching/nodes/{node_id}/quizzes", headers=student).json()[0]
    assert "answer" not in sq and sq["options"]
    tq = client.get(f"/api/v1/teaching/nodes/{node_id}/quizzes", headers=teacher).json()[0]
    assert tq["answer"] == "B"

    # 4) 学生答题：对 / 错 自动判分
    r = client.post(f"/api/v1/teaching/quizzes/{quiz_id}/answer", json={"answer": "B"}, headers=student)
    assert r.json()["is_correct"] is True and r.json()["score"] == 2
    r = client.post(f"/api/v1/teaching/quizzes/{quiz_id}/answer", json={"answer": "A"}, headers=student)
    assert r.json()["is_correct"] is False and r.json()["score"] == 0

    # 5) 学生写心得体会
    assert client.post(f"/api/v1/teaching/nodes/{node_id}/reflection",
                       json={"content": "本节理解了塞贝克效应"}, headers=student).status_code == 200

    # 6) 学生看自己的记录（2 次作答 + 1 条心得）
    logs = client.get("/api/v1/teaching/logs", headers=student).json()
    mine = [l for l in logs if l["node_id"] == node_id]
    assert len([l for l in mine if l["kind"] == "quiz_answer"]) >= 2
    assert any(l["kind"] == "reflection" for l in mine)

    # 7) 删除知识点级联（含子树与思考题）
    assert client.delete(f"/api/v1/teaching/nodes/{node_id}", headers=teacher).status_code == 200
    assert client.get(f"/api/v1/teaching/nodes/{node_id}", headers=teacher).status_code == 404


def test_teaching_multiple_choice_grading(client, make_user):
    teacher = make_user("t2", role="teacher")
    student = make_user("s2", role="student")
    nid = client.post("/api/v1/teaching/nodes", json={"title": "多选节点"}, headers=teacher).json()["id"]
    qid = client.post(f"/api/v1/teaching/nodes/{nid}/quizzes",
                      json={"qtype": "multiple", "stem": "多选?",
                            "options": [{"key": "A"}, {"key": "B"}, {"key": "C"}],
                            "answer": ["A", "C"], "score": 3}, headers=teacher).json()["id"]
    # 顺序无关，集合相等即满分
    r = client.post(f"/api/v1/teaching/quizzes/{qid}/answer", json={"answer": ["C", "A"]}, headers=student)
    assert r.json()["is_correct"] is True and r.json()["score"] == 3
    # 少选 → 错
    r = client.post(f"/api/v1/teaching/quizzes/{qid}/answer", json={"answer": ["A"]}, headers=student)
    assert r.json()["is_correct"] is False and r.json()["score"] == 0


def test_ai_graceful_without_llm(client, make_user):
    """CI 无 LLM_BASE_URL → AI 端点优雅降级（ai=False），不 500。"""
    teacher = make_user("ai_t", role="teacher")
    student = make_user("ai_s", role="student")
    nid = client.post("/api/v1/teaching/nodes", json={"title": "AI 测试节点"}, headers=teacher).json()["id"]
    r = client.post("/api/v1/teaching/ai/ask",
                    json={"node_id": nid, "question": "什么是塞贝克效应？"}, headers=student)
    assert r.status_code == 200 and r.json()["ai"] is False
    r = client.post(f"/api/v1/teaching/nodes/{nid}/ai-feedback", headers=student)
    assert r.status_code == 200 and r.json()["ai"] is False
