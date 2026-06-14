# 环境变量配置指南

**文件**：`.env`  
**位置**：项目根目录  
**状态**：✅ 已自动创建（部署脚本会自动处理）

---

## 🚀 快速开始

### 自动创建（推荐）
部署脚本 `deploy-to-cloud.sh` 会自动创建 `.env` 文件，无需手动操作。

### 手动创建
如需自定义配置，在远程服务器执行：

```bash
# 使用默认值创建
cat > /data/sensemble-platform/.env << 'EOF'
SECRET_KEY=change-me-in-prod-please
ACCESS_TOKEN_EXPIRE_MINUTES=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
CORS_ORIGINS=*
FRONTEND_PORT=80
RATE_LIMIT_MIN_INTERVAL=0
DB_HOST=db
DB_PORT=5432
DB_USER=sensemble
DB_PASSWORD=sensemble
DB_NAME=sensemble
MQTT_HOST=emqx
MQTT_PORT=1883
MQTT_TOPIC=sensemble/+/data
MQTT_ENABLED=true
MQTT_BACKEND_USER=backend-ingest
MQTT_BACKEND_PASSWORD=backend-ingest-secret
MQTT_AUTH_SECRET=change-me-internal
MINIO_ENDPOINT=minio:9000
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin
GRAFANA_PASSWORD=admin
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=qwen2.5:7b
EOF
```

---

## 📋 完整的环境变量说明

### 🔐 应用配置

| 变量 | 默认值 | 说明 | 生产环境必改 |
|---|---|---|---|
| `SECRET_KEY` | `change-me-in-prod-please` | JWT 密钥 | ✅ **必改** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Token 过期时间（分钟）| ❌ |
| `ADMIN_USERNAME` | `admin` | 默认管理员账号 | ⚠️ 建议改 |
| `ADMIN_PASSWORD` | `admin123` | 默认管理员密码 | ✅ **必改** |
| `CORS_ORIGINS` | `*` | CORS 允许来源 | ⚠️ 生产改为具体域名 |
| `FRONTEND_PORT` | `80` | 前端端口 | ❌ |
| `RATE_LIMIT_MIN_INTERVAL` | `0` | 设备上报速率限制（秒） | ⚠️ 生产建议 1.0 |

### 🗄️ 数据库配置

| 变量 | 默认值 | 说明 | 修改? |
|---|---|---|---|
| `DB_HOST` | `db` | 数据库主机 | ❌ 本地部署不改 |
| `DB_PORT` | `5432` | 数据库端口 | ❌ |
| `DB_USER` | `sensemble` | 数据库用户 | ⚠️ 可改 |
| `DB_PASSWORD` | `sensemble` | 数据库密码 | ✅ **生产必改** |
| `DB_NAME` | `sensemble` | 数据库名称 | ❌ |

### 📡 MQTT 配置

| 变量 | 默认值 | 说明 | 修改? |
|---|---|---|---|
| `MQTT_HOST` | `emqx` | MQTT 服务器地址 | ❌ 本地不改 |
| `MQTT_PORT` | `1883` | MQTT 端口 | ❌ |
| `MQTT_TOPIC` | `sensemble/+/data` | MQTT 主题模式 | ❌ |
| `MQTT_ENABLED` | `true` | 是否启用 MQTT | ❌ |
| `MQTT_BACKEND_USER` | `backend-ingest` | 后端服务用户 | ❌ |
| `MQTT_BACKEND_PASSWORD` | `backend-ingest-secret` | 后端服务密码 | ✅ 生产改 |
| `MQTT_AUTH_SECRET` | `change-me-internal` | MQTT 回调密钥 | ✅ **必改** |

### 📦 MinIO 配置（对象存储）

| 变量 | 默认值 | 说明 | 修改? |
|---|---|---|---|
| `MINIO_ENDPOINT` | `minio:9000` | MinIO 地址 | ❌ 本地不改 |
| `MINIO_USER` | `minioadmin` | MinIO 用户名 | ⚠️ 生产改 |
| `MINIO_PASSWORD` | `minioadmin` | MinIO 密码 | ✅ **生产必改** |

### 📊 Grafana 配置

| 变量 | 默认值 | 说明 | 修改? |
|---|---|---|---|
| `GRAFANA_PASSWORD` | `admin` | Grafana 管理员密码 | ✅ **生产必改** |

### 🤖 AI 助教配置（可选）

| 变量 | 默认值 | 说明 | 修改? |
|---|---|---|---|
| `LLM_BASE_URL` | 空 | LLM API 地址（本机 Ollama: http://host.docker.internal:11434/v1） | ⚠️ 可选 |
| `LLM_API_KEY` | 空 | LLM API 密钥（如使用云 API） | ⚠️ 可选 |
| `LLM_MODEL` | `qwen2.5:7b` | 使用的模型名称 | ⚠️ 可选 |

**说明**：如不填 LLM 配置，AI 助教功能会优雅降级（不可用但不影响其他功能）

---

## 🔐 生产环境安全清单

### 必须修改的项

```bash
# 1. 生成安全的 SECRET_KEY
openssl rand -hex 32

# 2. 修改所有密码
# - ADMIN_PASSWORD
# - DB_PASSWORD
# - MQTT_BACKEND_PASSWORD
# - MQTT_AUTH_SECRET
# - MINIO_PASSWORD
# - GRAFANA_PASSWORD

# 3. 修改 CORS_ORIGINS
# 从 "*" 改为具体的域名
CORS_ORIGINS=https://sensemble.org,https://www.sensemble.org

# 4. 启用速率限制
RATE_LIMIT_MIN_INTERVAL=1.0

# 5. 关闭调试模式（如有）
DEBUG=false
```

### 示例生产配置

```bash
cat > .env << 'EOF'
# 安全配置（示例，请替换为真实值）
SECRET_KEY=a7f3c9e2d4b1f6a8c5e0d9f2b4c6e8a0
ACCESS_TOKEN_EXPIRE_MINUTES=720
ADMIN_USERNAME=sensemble_admin
ADMIN_PASSWORD=ChangeMe@12345
CORS_ORIGINS=https://sensemble.org,https://www.sensemble.org
FRONTEND_PORT=80
RATE_LIMIT_MIN_INTERVAL=1.0

# 数据库
DB_HOST=db
DB_PORT=5432
DB_USER=sensemble
DB_PASSWORD=SecurePassword@2024
DB_NAME=sensemble

# MQTT
MQTT_HOST=emqx
MQTT_PORT=1883
MQTT_TOPIC=sensemble/+/data
MQTT_ENABLED=true
MQTT_BACKEND_USER=backend-ingest
MQTT_BACKEND_PASSWORD=BackendSecret@2024
MQTT_AUTH_SECRET=MqttAuthSecret@2024

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_USER=sensemble
MINIO_PASSWORD=MinioSecure@2024

# Grafana
GRAFANA_PASSWORD=GrafanaSecure@2024

# AI（可选）
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=deepseek-chat
EOF
```

---

## 🔄 更新密钥

### 更改 Admin 密码

```bash
# 进入容器
docker-compose -f docker-compose.prod.yml exec backend bash

# 使用 Python 修改
python3 << 'PYTHON'
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.security import hash_password

db = SessionLocal()
admin = db.execute(select(User).where(User.username == 'admin')).scalar()
if admin:
    admin.password_hash = hash_password('new_password_here')
    db.commit()
    print("✓ Admin password updated")
PYTHON
```

### 更改数据库密码

```bash
# 进入数据库容器
docker-compose -f docker-compose.prod.yml exec db psql -U sensemble

# SQL 命令
ALTER USER sensemble WITH PASSWORD 'new_password';
```

---

## 📋 检查清单

部署前验证：

- [ ] `.env` 文件存在于 `/data/sensemble-platform/`
- [ ] 所有必需变量都已设置（无空值）
- [ ] 生产环境已修改所有密码
- [ ] `SECRET_KEY` 已修改为强密钥
- [ ] `CORS_ORIGINS` 已设置为实际域名（如有）
- [ ] 容器可以正常启动（检查日志）

---

## 🚨 常见问题

### Q: 忘记了 Admin 密码怎么办？
A: 重置 Admin 密码：
```bash
docker-compose -f docker-compose.prod.yml exec backend python3 << 'EOF'
from app.database import SessionLocal
from app.models import User
from app.security import hash_password
from sqlalchemy import select

db = SessionLocal()
admin = db.execute(select(User).where(User.username == 'admin')).scalar()
if admin:
    admin.password_hash = hash_password('new_password')
    db.commit()
EOF
```

### Q: 如何验证 `.env` 是否正确加载？
A: 查看日志：
```bash
docker-compose -f docker-compose.prod.yml logs backend | grep -i "database\|connect"
```

### Q: 可以在容器运行时修改 `.env` 吗？
A: 不能。修改后需要重启容器：
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Q: LLM 配置如何启用？
A: 选择一个 LLM 提供商：

**选项 1：本地 Ollama**
```bash
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=any_value
LLM_MODEL=qwen2.5:7b
```

**选项 2：DeepSeek API**
```bash
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=deepseek-chat
```

**选项 3：禁用（留空）**
```bash
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

---

## 📚 相关文件

- [docker-compose.prod.yml](docker-compose.prod.yml) — Docker Compose 配置
- [deploy-to-cloud.sh](deploy-to-cloud.sh) — 自动部署脚本（自动创建 `.env`）
- [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md) — 完整部署指南

---

## ✅ 验证部署成功

```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 检查后端能否连接数据库
docker-compose -f docker-compose.prod.yml logs backend | head -20

# 测试 API
curl http://localhost:8000/docs

# 测试登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=admin123"
```

---

**最后更新**：2026-06-14  
**维护人员**：Claude Code  
**生产环境建议**：定期轮换密钥和敏感信息
