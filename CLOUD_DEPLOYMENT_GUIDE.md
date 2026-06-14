# 云端部署指南

**目标**：将 Sensemble 教学平台部署到远程服务器（149.248.16.187）  
**方式**：Git + Docker Compose  
**最后更新**：2026-06-14

---

## 📋 部署前准备

### 前置条件
- [ ] 远程服务器已安装 Docker 和 Docker Compose
- [ ] 可以 SSH 访问远程服务器（账号、密钥）
- [ ] 服务器有公网访问 GitHub 权限
- [ ] 8080 和 8000 端口未被占用

### 服务器要求
```
CPU：2 核以上
内存：4GB 以上
存储：20GB 以上（用于数据库和日志）
操作系统：Linux（推荐 Ubuntu 20.04+）
```

---

## 🚀 部署步骤

### 方式 A：使用自动化脚本（推荐）

#### 第一步：准备脚本
从本地下载 `deploy-to-cloud.sh` 到远程服务器：

```bash
# 在本地
scp deploy-to-cloud.sh root@149.248.16.187:/root/

# 或者在远程服务器上直接下载
cd /root
wget https://raw.githubusercontent.com/tonylxc/sensemble-platform/main/deploy-to-cloud.sh
chmod +x deploy-to-cloud.sh
```

#### 第二步：修改脚本配置
编辑脚本中的项目目录路径（如果需要）：

```bash
nano deploy-to-cloud.sh

# 找到这一行，根据实际情况修改
PROJECT_DIR="/data/sensemble-platform"
```

#### 第三步：执行部署脚本
```bash
sudo ./deploy-to-cloud.sh
```

脚本会自动执行以下步骤：
1. ✅ 更新 Git 代码
2. ✅ 停止旧容器
3. ✅ 重新构建镜像
4. ✅ 启动新容器
5. ✅ 验证部署

---

### 方式 B：手动部署

#### 第一步：SSH 连接到服务器
```bash
ssh root@149.248.16.187
```

#### 第二步：克隆或更新代码
```bash
# 首次部署：克隆代码
cd /data
git clone https://github.com/tonylxc/sensemble-platform.git
cd sensemble-platform

# 已有代码：更新到最新版本
cd /data/sensemble-platform
git fetch origin
git pull origin main
```

#### 第三步：停止旧容器（如果存在）
```bash
docker-compose -f docker-compose.prod.yml down
```

#### 第四步：重新构建镜像
```bash
docker-compose -f docker-compose.prod.yml build --no-cache
```

#### 第五步：启动新容器
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 第六步：验证部署
```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 检查后端日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查前端日志
docker-compose -f docker-compose.prod.yml logs frontend

# 测试 API
curl -s http://localhost:8000/docs | head -20
```

---

## ✅ 部署验证

### 检查清单
```bash
# 1. 容器状态
docker-compose -f docker-compose.prod.yml ps

# 输出应该显示：
# NAME                              STATUS
# sensemble-platform-backend-1      Up XX seconds
# sensemble-platform-frontend-1     Up XX seconds
# sensemble-platform-db-1           Up XX seconds (healthy)
# sensemble-platform-emqx-1         Up XX seconds
```

### 访问应用
```
前端：http://149.248.16.187:8080
API 文档：http://149.248.16.187:8000/docs
```

### 测试功能
1. **前端应访问**
   ```
   打开浏览器访问 http://149.248.16.187:8080
   应该看到登录页面
   ```

2. **API 测试**
   ```bash
   # 获取 API 文档
   curl -s http://149.248.16.187:8000/docs
   
   # 登录
   curl -X POST http://149.248.16.187:8000/api/v1/auth/login \
     -d "username=teacher_sync&password=test123456"
   
   # 查询知识点
   curl -H "Authorization: Bearer <token>" \
     http://149.248.16.187:8000/api/v1/teaching/nodes?course_code=EE-TEST-2026
   ```

3. **教学平台测试**
   ```
   打开 http://149.248.16.187:8080
   登录：teacher_sync / test123456
   导航：教学中心
   检查：公式应该清晰显示（不是乱码）
   ```

---

## 🔄 常见操作

### 查看日志
```bash
# 实时查看后端日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 查看前端日志
docker-compose -f docker-compose.prod.yml logs -f frontend

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs db
```

### 重启容器
```bash
# 重启所有容器
docker-compose -f docker-compose.prod.yml restart

# 重启特定容器
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart frontend
```

### 更新代码
```bash
# 更新代码并重新部署
cd /data/sensemble-platform
git pull origin main
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml restart
```

### 数据库备份
```bash
# 备份数据库
docker-compose -f docker-compose.prod.yml exec db pg_dump -U sensemble sensemble > backup.sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T db psql -U sensemble sensemble < backup.sql
```

### 清理存储
```bash
# 删除未使用的镜像
docker image prune -a

# 删除未使用的容器
docker container prune

# 删除所有 Docker 数据（谨慎！）
docker system prune -a --volumes
```

---

## 🚨 故障排除

### 问题 1：容器启动失败
**症状**：`docker-compose ps` 显示容器 Exit 或 Restarting

**解决**：
```bash
# 查看错误日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查端口是否被占用
netstat -tulpn | grep 8000
netstat -tulpn | grep 8080

# 如果端口被占用，修改 docker-compose.prod.yml 中的端口映射
```

### 问题 2：API 返回 404
**症状**：访问 `/api/v1/teaching/nodes` 返回 404

**解决**：
```bash
# 检查后端日志是否有教学模块导入错误
docker-compose logs backend | grep -i "teaching\|error"

# 重新构建后端
docker-compose -f docker-compose.prod.yml build --no-cache backend
docker-compose -f docker-compose.prod.yml restart backend
```

### 问题 3：数据库连接失败
**症状**：后端日志显示 `FATAL: database "sensemble" does not exist`

**解决**：
```bash
# 初始化数据库
docker-compose -f docker-compose.prod.yml down
docker volume rm sensemble-platform_postgres_data  # 删除旧数据
docker-compose -f docker-compose.prod.yml up -d db
docker-compose -f docker-compose.prod.yml up -d backend

# 等待初始化完成
sleep 30
docker-compose logs backend
```

### 问题 4：公式显示为乱码
**症状**：教学页面中 $ ... $ 显示为乱码

**解决**：
```bash
# 清除浏览器缓存（Ctrl+Shift+Delete）
# 或者重新构建前端
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml restart frontend

# 访问浏览器后清除缓存：F12 → Application → Clear Site Data
```

---

## 📊 部署后的维护

### 日常检查
```bash
# 每天运行一次检查脚本
docker-compose -f docker-compose.prod.yml ps

# 监控磁盘空间
df -h /data

# 监控 Docker 镜像大小
docker images
```

### 定期备份
```bash
# 创建 cron 任务自动备份（每天凌晨 2 点）
0 2 * * * /data/sensemble-platform/backup.sh

# backup.sh 内容：
#!/bin/bash
cd /data/sensemble-platform
docker-compose exec -T db pg_dump -U sensemble sensemble | \
  gzip > /backup/sensemble-$(date +%Y%m%d).sql.gz
find /backup -mtime +30 -delete  # 删除 30 天前的备份
```

### 安全加固
```bash
# 1. 启用 HTTPS（使用 Certbot + Let's Encrypt）
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d sensemble.org

# 2. 配置 Nginx SSL（修改 nginx 配置）
# 3. 启用防火墙
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 4. 更改默认密码
# 更新数据库中的教师账号密码
```

---

## 📞 获取帮助

### 查看日志
```bash
# 实时监控所有日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs backend | tail -50
```

### 诊断脚本
```bash
# 保存为 diagnose.sh 并运行
#!/bin/bash
echo "=== Docker 状态 ==="
docker-compose -f docker-compose.prod.yml ps

echo "=== 端口占用 ==="
netstat -tulpn | grep -E "8000|8080"

echo "=== 磁盘空间 ==="
df -h /data

echo "=== 后端日志（最后 20 行） ==="
docker-compose -f docker-compose.prod.yml logs backend | tail -20

echo "=== 数据库连接测试 ==="
docker-compose -f docker-compose.prod.yml exec -T db psql -U sensemble -c "SELECT version();"
```

---

## ✅ 部署检查清单

- [ ] 服务器已安装 Docker 和 Docker Compose
- [ ] SSH 访问正常
- [ ] 代码已克隆到 `/data/sensemble-platform`
- [ ] 所有容器都在运行（`docker-compose ps`）
- [ ] 前端可访问：http://149.248.16.187:8080
- [ ] API 可访问：http://149.248.16.187:8000/docs
- [ ] 能登录教学平台
- [ ] 公式显示正确（无乱码）
- [ ] 数据库备份已配置
- [ ] 防火墙规则已配置

---

## 🎉 恭喜！

您的 Sensemble 教学平台已成功部署到云端！

**部署完成**：2026-06-14  
**部署位置**：149.248.16.187  
**服务状态**：✅ 生产环境就绪

**后续建议**：
1. 定期备份数据库
2. 监控服务器资源使用
3. 定期更新依赖包和 Docker 镜像
4. 收集用户反馈并迭代功能

有问题？查看日志、检查防火墙、验证 DNS 配置。
