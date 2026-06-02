# 众感 Sensemble — 开放感知数据平台（MVP 骨架）

面向高校教学与科研的开放感知数据平台。本仓库是 **MVP 技术骨架**，打通核心闭环：
> 注册 → 注册设备(领 Token) → HTTP/MQTT 上报 → 入时序库 → 查询/可视化 → 打包数据集(算 DQS) → 教师审核 → 发布 → 检索/下载。

## 技术栈
- **后端**：Python FastAPI（异步、自动 OpenAPI/Swagger）+ SQLAlchemy 2.0
- **数据库**：PostgreSQL + TimescaleDB（时序）+ PostGIS（空间，P1）
- **接入**：HTTP(S) + MQTT（EMQX）
- **存储**：MinIO（原始文件，P1）
- **编排**：Docker Compose 单机（K8s 留 P2）

## 目录结构
```
sensemble-platform/
├─ docker-compose.yml          # 一键起 db/emqx/minio/backend/frontend
├─ .env.example                # 配置样例（复制为 .env）
├─ .github/workflows/ci.yml    # CI：后端 pytest + 前端 build
├─ db/init/001_init.sql        # 建表 + 超表 + 索引（DB 首启自动执行）
├─ emqx/emqx.conf              # EMQX 一机一 Token 认证/授权（回调后端）
├─ docs/openapi.yaml           # 人读接口契约（运行后 /docs 为自动版）
├─ tools/simulate.py           # 造数脚本（建设备 / 回填 / 实时上报）
├─ backend/
│  ├─ Dockerfile  requirements.txt  requirements-dev.txt  pytest.ini
│  ├─ app/
│  │  ├─ main.py               # FastAPI 入口、启动建管理员、起 MQTT 线程
│  │  ├─ config.py database.py security.py audit.py
│  │  ├─ models.py schemas.py deps.py
│  │  ├─ dqs.py                # DQS v1 三维算法
│  │  ├─ idw.py                # IDW 空间插值
│  │  ├─ mqtt_ingest.py        # MQTT 订阅入库
│  │  └─ routers/ auth.py devices.py data.py datasets.py internal.py
│  └─ tests/                   # pytest：auth/devices/data/datasets/dqs/idw/mqtt_auth
└─ frontend/
   ├─ web/                     # Vue3+Vite+Pinia 真实前端（Dockerfile + nginx.conf）
   └─ prototype/               # 单文件高保真原型
```

## 快速开始
```bash
cp .env.example .env          # 按需改密码/SECRET_KEY
docker compose up -d --build
```
启动后（一条命令起全栈，含前端）：
- **前端 Web：http://localhost:8080**（nginx 托管 Vue 构建产物，`/api` 同源代理到后端）
- API + Swagger：http://localhost:8000/docs
- EMQX 控制台：http://localhost:18083 （默认 admin/public）
- MinIO 控制台：http://localhost:9001
- 默认管理员：`admin` / `admin123`（来自 .env）

> 前端开发模式（热重载）：另开终端 `cd frontend/web && npm install && npm run dev` → http://localhost:5173
> 造数据：`pip install -r tools/requirements.txt && python tools/simulate.py`（详见 tools/README.md）

## 端到端冒烟测试（curl）
```bash
# 1) 注册一个老师 + 一个学生
curl -s -XPOST localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
  -d '{"username":"teacher1","password":"pass","role":"teacher"}'
curl -s -XPOST localhost:8000/api/v1/auth/register -H "Content-Type: application/json" \
  -d '{"username":"stud1","password":"pass","role":"student"}'

# 2) 学生登录拿 JWT（注意 login 用表单）
STU=$(curl -s -XPOST localhost:8000/api/v1/auth/login -d "username=stud1&password=pass" | jq -r .access_token)

# 3) 注册设备 → 返回一次性 device_token
curl -s -XPOST localhost:8000/api/v1/devices -H "Authorization: Bearer $STU" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"esp32-001","type":"ESP32","location":"教学楼A-301","lat":30.12,"lon":120.65,"sample_interval":60,"sensors":{"DHT22":{"accuracy":0.5}}}'
# 复制返回的 device_token 到 DTOK
DTOK=...

# 4) 设备 HTTP 上报（一批点）
curl -s -XPOST localhost:8000/api/v1/data -H "X-Device-Id: esp32-001" -H "X-Device-Token: $DTOK" \
  -H "Content-Type: application/json" \
  -d '[{"metric":"temperature","value":23.5},{"metric":"humidity","value":45.2}]'

# 5) 查询时序
curl -s "localhost:8000/api/v1/data?device_id=esp32-001&metric=temperature" -H "Authorization: Bearer $STU"

# 6) 打包数据集（自动算 DQS）
curl -s -XPOST localhost:8000/api/v1/datasets -H "Authorization: Bearer $STU" -H "Content-Type: application/json" \
  -d '{"name":"A301温湿度","device_id":"esp32-001","start":"2026-06-01T00:00:00Z","end":"2026-06-08T00:00:00Z",
       "meta":{"sensor_type":"DHT22","accuracy":"±0.5℃","sample_interval":60,"location":"A-301","calibration_date":"2026-05-30"}}'
# → 复制 dataset_id 到 DID

# 7) 提交审核 → 老师审核通过
curl -s -XPOST localhost:8000/api/v1/datasets/$DID/submit -H "Authorization: Bearer $STU"
TEA=$(curl -s -XPOST localhost:8000/api/v1/auth/login -d "username=teacher1&password=pass" | jq -r .access_token)
curl -s -XPOST localhost:8000/api/v1/datasets/$DID/review -H "Authorization: Bearer $TEA" \
  -H "Content-Type: application/json" -d '{"result":"approved","comment":"元数据完整，通过"}'

# 8) 检索 + 下载 CSV
curl -s "localhost:8000/api/v1/datasets?keyword=温湿度&sort=dqs" -H "Authorization: Bearer $STU"
curl -s "localhost:8000/api/v1/datasets/$DID/download?format=csv" -H "Authorization: Bearer $STU"
```

## MQTT 上报示例（一机一 Token，EMQX 侧认证）
设备连接时 `username=device_id`、`password=设备Token`，由 EMQX 回调后端校验；未授权设备**连不上**。
```bash
mosquitto_pub -h localhost -p 1883 \
  -u "esp32-001" -P "<device_token>" \
  -t "sensemble/esp32-001/data" \
  -m '{"data":[{"metric":"temperature","value":24.1}]}'
```

### 认证/授权机制
- `emqx/emqx.conf` 配置 EMQX 5.x 的 **HTTP 认证 + HTTP 授权**，回调后端：
  - `POST /internal/mqtt/auth`：校验 `username/password`（设备 Token 的 sha256），后端 ingest 用服务账号登录并返回 `is_superuser`。
  - `POST /internal/mqtt/acl`：设备只能 pub/sub 自己的 `sensemble/{device_id}/#`（`no_match=deny`）。
- 共享密钥：`emqx.conf` 的 `x-emqx-secret` 必须等于后端 `.env` 的 `MQTT_AUTH_SECRET`。
- 后端 ingest 消费者用 `MQTT_BACKEND_USER/PASSWORD` 登录（超级用户，可订阅 `sensemble/+/data`）。

> 等价做法：也可不用配置文件，改在 EMQX Dashboard（:18083）或 REST API `/api/v5/authentication`、`/api/v5/authorization/sources` 配置同样的 HTTP 认证/授权源。生产请对内部回调启用 TLS。

## 已实现 / 待补
**✅ 已实现**
- 用户 / RBAC、设备注册 + **一机一 Token**、HTTP + MQTT 接入、时序入库 / 查询
- 元数据 + **DQS v1（三维）**、数据集 打包 / 提交 / 审核 / 发布 / 检索 / 下载、审计日志
- **IDW 空间热力图**（后端 numpy 插值 + 前端 ECharts 渲染）
- **EMQX 一机一 Token 认证 / 授权**（连接级鉴权 + 主题隔离，未授权设备连不上）
- **Vue3 真实前端**（登录 / 概览 / 设备 / 可视化 / 数据集 / 审核）+ 单文件高保真原型
- **造数脚本**（建设备 + 回填历史 + 实时上报，HTTP/MQTT）
- **Docker Compose 全栈**（含前端 nginx）+ **pytest / GitHub Actions CI**
- **PII / 敏感信息扫描**（数据集提交时拦截身份证/手机/邮箱/银行卡/敏感词，FR-9.2/10.2）
- **对外开放 API + API Key**（第三方只读访问"已发布且公开"数据集，FR-12.1）
- **Prometheus + Grafana 监控**（后端 /metrics + 预置面板，FR-15.2）
- **DQS 五维完整版**（完整度 / 时序连续性 / 元数据 / 校准 / 异常率，FR-6.2）
- **站内通知**（审核通过/退回自动通知作者，FR-13.1）+ **运营统计报表**（用户/设备/数据/数据集/下载/质量分级，FR-14.1）
- **设备在线状态判定 + 停用/注销**（FR-2.3 / FR-2.5）

**⏳ P1（剩余）**：MinIO 原始件归档、设备离线主动告警（定时任务）、上报限流、型号词典/版本历史、JS/Python SDK

**⏳ P2（生态 / 高级）**：Kriging 高级插值、DOI / 版本管理、智能推荐、K8s、校 CAS 统一身份

## 测试与 CI
后端测试用 pytest（覆盖注册/登录/RBAC、设备 Token、上报/查询、数据集全流程与 DQS）。
```bash
# 本地：需一个测试库（与开发库分开，避免被 TRUNCATE）
docker compose exec db createdb -U sensemble sensemble_test   # 或用任意 PG
cd backend
pip install -r requirements.txt -r requirements-dev.txt
DB_NAME=sensemble_test MQTT_ENABLED=false pytest -q
```
CI：`.github/workflows/ci.yml` 在每次 push/PR 自动跑 **后端 pytest（起 postgres 服务）** + **前端 vite build**，骨架被改坏即红灯。

## 对外开放 API 与监控（P1）
**开放 API（API Key）**：登录后创建 Key，第三方据此只读访问"已发布且公开"的数据集（不暴露私有数据）。
```bash
curl -s -XPOST "localhost:8000/api/v1/keys?name=research" -H "Authorization: Bearer $JWT"   # 返回 api_key 仅显示一次
curl -s localhost:8000/api/v1/open/datasets -H "X-API-Key: sk_xxx"
curl -s "localhost:8000/api/v1/open/datasets/SMDP-2026-0001/download?format=csv" -H "X-API-Key: sk_xxx"
```
**监控**：后端 `/metrics` 暴露 Prometheus 指标 → Prometheus(:9090) 抓取 → Grafana(:3000，密码见 .env 的 GRAFANA_PASSWORD) 预置"众感后端监控"面板（请求速率 / 时延 P95 / 状态码 / 5xx 错误率）。生产中 9090/3000 仅绑 127.0.0.1，用 SSH 隧道访问：
```bash
ssh -L 3000:localhost:3000 root@<server>    # 然后本机浏览器开 http://localhost:3000
```
**PII 扫描**：数据集提交时自动检测身份证/手机号/邮箱/银行卡/敏感词，命中即拒绝并提示，从源头防止隐私上链。

> 说明：本骨架供开发起步；生产上线前请补 TLS（含 EMQX 与内部回调）、接口限流、数据备份与压力测试。
