#!/bin/bash
# 诊断脚本：检查所有容器和网络连接

echo "════════════════════════════════════════"
echo "Sensemble 平台 - 诊断脚本"
echo "════════════════════════════════════════"
echo ""

cd /data/sensemble-platform

echo "[1] Docker 容器状态"
echo "────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml ps
echo ""

echo "[2] 检查后端是否运行"
echo "────────────────────────────────────────"
if docker-compose -f docker-compose.prod.yml ps backend | grep -q "Up"; then
    echo "✅ 后端容器运行中"
else
    echo "❌ 后端容器未运行"
fi
echo ""

echo "[3] 检查前端是否运行"
echo "────────────────────────────────────────"
if docker-compose -f docker-compose.prod.yml ps frontend | grep -q "Up"; then
    echo "✅ 前端容器运行中"
else
    echo "❌ 前端容器未运行"
fi
echo ""

echo "[4] 测试本机 API 访问 (:8000)"
echo "────────────────────────────────────────"
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ API 可访问"
else
    echo "❌ API 无法访问"
fi
echo ""

echo "[5] 测试本机前端访问 (:8080)"
echo "────────────────────────────────────────"
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ 前端可访问"
else
    echo "❌ 前端无法访问"
fi
echo ""

echo "[6] 端口监听状态"
echo "────────────────────────────────────────"
echo "监听 8000 的进程："
netstat -tulpn 2>/dev/null | grep :8000 || echo "未监听"
echo ""
echo "监听 8080 的进程："
netstat -tulpn 2>/dev/null | grep :8080 || echo "未监听"
echo ""

echo "[7] 后端日志（最后 20 行）"
echo "────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml logs backend | tail -20
echo ""

echo "[8] 前端日志（最后 20 行）"
echo "────────────────────────────────────────"
docker-compose -f docker-compose.prod.yml logs frontend | tail -20
echo ""

echo "════════════════════════════════════════"
echo "诊断完成"
echo "════════════════════════════════════════"
