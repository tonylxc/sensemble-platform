#!/bin/bash
# 部署脚本：在远程服务器上执行此脚本以部署最新代码

set -e  # 发生错误时退出

echo "════════════════════════════════════════"
echo "Sensemble 平台 - 云端部署脚本"
echo "════════════════════════════════════════"
echo ""

# 配置
PROJECT_DIR="/data/sensemble-platform"  # 根据实际情况修改
REPO_URL="https://github.com/tonylxc/sensemble-platform.git"
BRANCH="main"

# 第一步：更新代码
echo "[1/5] 更新代码库..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
else
    echo "[!] 目录不存在或不是 Git 仓库"
    echo "正在克隆新仓库..."
    mkdir -p "$(dirname "$PROJECT_DIR")"
    git clone -b $BRANCH $REPO_URL "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo "[✓] 代码已更新"
echo ""

# 第二步：停止当前容器
echo "[2/5] 停止现有容器..."
docker-compose -f docker-compose.prod.yml down || true
echo "[✓] 容器已停止"
echo ""

# 第三步：重建镜像
echo "[3/5] 重新构建 Docker 镜像..."
docker-compose -f docker-compose.prod.yml build --no-cache
echo "[✓] 镜像构建完成"
echo ""

# 第四步：启动新容器
echo "[4/5] 启动新容器..."
docker-compose -f docker-compose.prod.yml up -d
echo "[✓] 容器已启动"
echo ""

# 第五步：验证部署
echo "[5/5] 验证部署..."
sleep 5

# 检查容器状态
BACKEND_STATUS=$(docker-compose -f docker-compose.prod.yml ps backend | grep -c "Up" || true)
FRONTEND_STATUS=$(docker-compose -f docker-compose.prod.yml ps frontend | grep -c "Up" || true)

if [ "$BACKEND_STATUS" -eq 1 ] && [ "$FRONTEND_STATUS" -eq 1 ]; then
    echo "[✓] 所有容器都在运行"
    echo ""
    echo "════════════════════════════════════════"
    echo "✅ 部署成功！"
    echo "════════════════════════════════════════"
    echo ""
    echo "访问地址："
    echo "  前端：http://149.248.16.187:8080"
    echo "  API：http://149.248.16.187:8000"
    echo ""
    echo "Docker 容器状态："
    docker-compose -f docker-compose.prod.yml ps
else
    echo "[!] 容器启动异常，请检查日志"
    echo ""
    echo "后端日志："
    docker-compose -f docker-compose.prod.yml logs backend | tail -10
    echo ""
    echo "前端日志："
    docker-compose -f docker-compose.prod.yml logs frontend | tail -10
    exit 1
fi
