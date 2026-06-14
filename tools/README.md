# 众感 Sensemble - 工具脚本集

## 📚 sync_knowledge.py — 知识点同步工具

用于将本地 Markdown 文件的知识点批量同步到 Sensemble 教学平台后端。

### 功能特性

- ✅ **异步 HTTP 请求**：基于 `httpx` + `asyncio`，支持高效批量同步
- ✅ **YAML 元数据解析**：支持在 Markdown 前置（frontmatter）中定义 title、difficulty、tags 等
- ✅ **自动树状结构**：通过 `parent` 字段自动建立知识点的父子关系
- ✅ **增量同步**：按标题 + 父节点匹配，重复运行时仅更新变化的内容
- ✅ **双向同步**：支持创建（POST）和更新（PATCH）操作
- ✅ **错误恢复**：详细的日志和异常处理，单个文件失败不影响整个同步过程
- ✅ **模拟运行**：`--dry-run` 模式预览所有操作，无需真实提交

### 快速开始

#### 1. 安装依赖
```bash
pip install -r tools/requirements.txt
```

#### 2. 同步知识点
```bash
# 同步整个目录
python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101

# 模拟运行（预览）
python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101 --dry-run
```

#### 3. Markdown 文件格式
```markdown
---
title: 1.1 塞贝克效应
difficulty: 中级
tags: [热电效应, 温度测量]
parent: 第1章 传感器基础
---

# 正文标题

内容支持 **Markdown** 和 $LaTeX$ 公式...
```

### 详细文档

见本文件下方或访问项目 Wiki

---

## 使用示例

### 基础命令

```bash
# 同步整个目录到 EE101 课程
python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101

# 同步单个文件
python tools/sync_knowledge.py --file docs/knowledge/ch1/intro.md --course EE101

# 指定后端地址
python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101 \
  --api http://192.168.1.100:8000

# 带认证令牌
python tools/sync_knowledge.py --dir docs/knowledge/ch1 --course EE101 \
  --token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 输出示例

```
📚 开始同步 2 个文件到课程 'EE101'
   后端地址：http://localhost:8000

✓ 新建 '第1章 传感器基础' (ID=1)
✓ 新建 '1.1 塞贝克效应' (ID=2)

✓ 同步完成：新建 2，更新 0，失败 0
```

---

## 故障排除

### 无法连接后端
```bash
# 检查后端是否启动
docker compose ps

# 测试 API 连接
curl http://localhost:8000/api/v1/teaching/nodes
```

### 认证失败
检查 JWT token 是否有效，可通过后端的 login 端点获取。

### 父知识点不存在
确保父知识点已先创建，或移除 YAML 中的 `parent` 字段。

---

## 更多功能

详见脚本顶部注释和 `--help` 选项。
