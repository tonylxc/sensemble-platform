# 众感 Sensemble · 教学模块 API 参考

> 教学与互动模块（知识点 / 思考题 / 学生记录 / AI 助教）的后端接口与数据模型说明，供团队查阅。
> 代码位置：模型与异步引擎 [`app/teaching.py`](teaching.py)；路由与 Pydantic [`app/routers/teaching.py`](routers/teaching.py)。

---

## 一、架构与独立性

- **独立技术栈**：教学模块用 **独立 `Base`（独立 metadata）+ 异步引擎（SQLAlchemy 2.0 async + asyncpg）**，与设备侧的同步栈（psycopg2）**共用同一个 PostgreSQL、互不干扰**。
- **不破坏设备表**：`init_teaching_models()` 启动时只 `create_all` 本模块的 3 张表（`course_nodes` / `quizzes` / `student_logs`），不创建、不修改、不依赖 `users / devices / sensor_data` 等设备表。
- **仅逻辑关联**：`student_logs.user_id`、`device_id` 为普通带索引列，**不设外键**指向设备表；只有教学三表之间（node→quiz→log）才用外键。
- **鉴权复用**：复用设备侧的 `get_current_user` / `require_roles`（同步依赖，FastAPI 线程池解析）。
- **容错**：路由挂载与建表均在 `main.py` 用 try/except 包裹，教学模块异常**不影响平台启动**。

接口前缀：`/api/v1/teaching`

---

## 二、数据模型

### 1. CourseNode —— 知识点（表 `course_nodes`，树状）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int, PK | |
| `parent_id` | int, 可空, FK→course_nodes.id (ON DELETE CASCADE) | 上级知识点；空=根 |
| `title` | varchar(200) | 标题 |
| `content` | text, 可空 | 富文本内容（HTML / Markdown） |
| `order_index` | int, 默认 0 | 同级排序 |
| `course_code` | varchar(64), 可空, 索引 | 归属课程（逻辑标识） |
| `created_at` / `updated_at` | timestamptz | |

关系：`parent` / `children`（自引用，删父级级联删子树）、`quizzes`。

### 2. Quiz —— 思考题（表 `quizzes`）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int, PK | |
| `node_id` | int, FK→course_nodes.id (CASCADE) | 所属知识点 |
| `qtype` | enum | `single` 单选 / `multiple` 多选 / `short_answer` 简答 |
| `stem` | text | 题干 |
| `options` | jsonb, 可空 | 选项数组 `[{"key":"A","text":"…"}]`（简答可空） |
| `answer` | jsonb, 可空 | 参考答案：单选 `"A"`；多选 `["A","C"]`；简答参考文本/要点 |
| `score` | float, 默认 1.0 | 分值 |
| `created_at` | timestamptz | |

关系：`node`、`logs`。

### 3. StudentLog —— 学生记录（表 `student_logs`，按事件分行）

> 即"学生提交数据"。心得、每次答题、每次 AI 问答各为一行，便于留痕与逐题统计。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int, PK | |
| `user_id` | int, 索引（**无外键**，逻辑关联设备侧 users） | 学生 |
| `device_id` | varchar(64), 可空, 索引（**无外键**） | 关联设备（可选） |
| `node_id` | int, FK→course_nodes.id (CASCADE) | 知识点 |
| `quiz_id` | int, 可空, FK→quizzes.id (CASCADE) | 关联题目（答题时） |
| `kind` | enum | `reflection` 心得 / `quiz_answer` 答题 / `ai_chat` AI问答 |
| `content` | text, 可空 | 心得正文 / 简答正文 / AI 提问 |
| `answer` | jsonb, 可空 | 选择题作答 / AI 回答 |
| `is_correct` | bool, 可空 | 自动判分结果（简答为 null） |
| `score` | float, 可空 | 得分 |
| `created_at` | timestamptz | |

复合索引：`(user_id, node_id)`。

---

## 三、枚举

| 枚举 | 取值 |
|---|---|
| `QuizType` | `single` · `multiple` · `short_answer` |
| `LogKind` | `reflection` · `quiz_answer` · `ai_chat` |

---

## 四、API 端点

> 凭据：所有端点需登录（`Authorization: Bearer <JWT>`）。标「教师」者需 teacher/admin 角色。
> 学生调用列题/节点详情时，**返回中不含 `answer` 字段**（不泄露答案）。

| 方法 | 路径 | 作用 | 权限 |
|---|---|---|---|
| GET | `/nodes?course_code=` | 知识点树（嵌套 children） | 登录 |
| POST | `/nodes` | 新建知识点 | 教师 |
| GET | `/nodes/{id}` | 节点详情 + 思考题 | 登录 |
| PATCH | `/nodes/{id}` | 修改知识点 | 教师 |
| DELETE | `/nodes/{id}` | 删除（级联子树/题/记录） | 教师 |
| POST | `/nodes/{node_id}/quizzes` | 新增思考题 | 教师 |
| GET | `/nodes/{node_id}/quizzes` | 列思考题 | 登录 |
| DELETE | `/quizzes/{id}` | 删除思考题 | 教师 |
| POST | `/quizzes/{id}/answer` | 提交作答（**自动判分**） | 登录 |
| POST | `/nodes/{id}/reflection` | 提交心得体会 | 登录 |
| GET | `/logs?node_id=&student_id=` | 学习记录（学生看自己/教师看全部） | 登录 |
| POST | `/ai/ask` | AI 答疑（以知识点为背景） | 登录 |
| POST | `/nodes/{id}/ai-feedback` | AI 学习反馈（汇总心得+答题） | 登录 |

### 请求/响应示例

**新建知识点**
```http
POST /api/v1/teaching/nodes
{ "title": "1.1 热电效应", "content": "<p>…</p>", "parent_id": 1, "order_index": 0, "course_code": "EE101" }
→ { "id": 12, "parent_id": 1, "title": "1.1 热电效应", "content": "<p>…</p>", "order_index": 0, "course_code": "EE101" }
```

**新增思考题（单选）**
```http
POST /api/v1/teaching/nodes/12/quizzes
{ "qtype": "single", "stem": "热电偶基于哪种效应？",
  "options": [{"key":"A","text":"光电"},{"key":"B","text":"塞贝克"}], "answer": "B", "score": 2 }
```

**学生作答（自动判分）**
```http
POST /api/v1/teaching/quizzes/101/answer
{ "answer": "B" }            # 多选传数组 ["A","C"]；简答传字符串
→ { "log_id": 55, "is_correct": true, "score": 2 }
```

**提交心得**
```http
POST /api/v1/teaching/nodes/12/reflection
{ "content": "本节理解了塞贝克效应…" }
→ { "log_id": 56 }
```

**AI 答疑 / 学习反馈**
```http
POST /api/v1/teaching/ai/ask            { "node_id": 12, "question": "塞贝克与帕尔贴效应的区别？" }
→ { "answer": "…", "ai": true }          # 未配置 LLM 时 ai=false 并返回提示，不报错

POST /api/v1/teaching/nodes/12/ai-feedback
→ { "feedback": "…", "ai": true }
```

---

## 五、自动判分规则（`grade_choice`）

| 题型 | 判定 | 返回 |
|---|---|---|
| `single` | 提交值 == `answer` | `(is_correct, score 或 0)` |
| `multiple` | 集合相等（顺序无关） | `(is_correct, score 或 0)` |
| `short_answer` | 不自动判分 | `(null, 0.0)`，留教师评阅 |

---

## 六、AI 助教与配置

- 走 **OpenAI 兼容** `/v1/chat/completions`，答疑以知识点 `title+content` 为背景；反馈汇总该生在该知识点的心得与答题。
- 通过环境变量配置（`.env`），**留空即禁用并优雅降级**（接口返回 `ai:false` 提示，不报错）：

```bash
# 本机 Ollama（compose 已配 extra_hosts 让后端容器可达宿主机）
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=qwen2.5:7b
# 或外部 API
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-xxxx
LLM_MODEL=deepseek-chat
```

---

## 七、前端对接

- API 封装：[`frontend/web/src/api/index.js`](../../frontend/web/src/api/index.js) 的 `teachingApi`。
- 页面：[`frontend/web/src/views/teaching/Teaching.vue`](../../frontend/web/src/views/teaching/Teaching.vue)。
- 路由：`/teaching`、`/course/learning`（侧栏「🎓 教学中心」）。
