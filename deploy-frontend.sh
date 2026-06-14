#!/bin/bash
# Sensemble 前端部署脚本
set -e

echo "=== Sensemble 前端部署 ==="

# 第 1 步：解压前端文件
echo "1️⃣  解压前端文件..."
cd /tmp
tar -xzf dist.tar.gz
ls -lah dist/

# 第 2 步：备份旧版本（如果存在）
NGINX_HTML="/usr/share/nginx/html"
if [ -d "$NGINX_HTML/old" ]; then
  echo "📦 清除上次备份..."
  rm -rf "$NGINX_HTML/old"
fi

if [ -d "$NGINX_HTML/assets" ] || [ -f "$NGINX_HTML/index.html" ]; then
  echo "📦 备份旧版本到 $NGINX_HTML/old ..."
  mkdir -p "$NGINX_HTML/old"
  mv "$NGINX_HTML"/* "$NGINX_HTML/old/" 2>/dev/null || true
fi

# 第 3 步：部署新版本
echo "2️⃣  部署新版本..."
cp -r dist/* "$NGINX_HTML/"
ls -lah "$NGINX_HTML/"

# 第 4 步：验证文件
echo "3️⃣  验证文件..."
test -f "$NGINX_HTML/index.html" && echo "✅ index.html 存在"
test -d "$NGINX_HTML/assets" && echo "✅ assets 目录存在"
test -f "$NGINX_HTML/assets"/*.js && echo "✅ JS 文件存在"
ls "$NGINX_HTML/assets" | grep -i katex && echo "✅ KaTeX 字体已包含" || echo "⚠️  未找到 KaTeX 字体"

# 第 5 步：检查 nginx 配置
echo ""
echo "4️⃣  检查 nginx 配置..."
if [ -f "$NGINX_HTML/../nginx/conf.d/default.conf" ]; then
  echo "✅ 检测到 default.conf"
  cat "$NGINX_HTML/../nginx/conf.d/default.conf" | head -20
fi

# 第 6 步：重启 nginx（Docker）
echo ""
echo "5️⃣  重启 nginx 容器..."
cd /opt/sensemble-platform
docker compose -f docker-compose.prod.yml restart nginx
sleep 2

# 第 7 步：验证部署
echo ""
echo "6️⃣  验证部署..."
if curl -s http://localhost/ | grep -q "<!DOCTYPE html"; then
  echo "✅ 前端已部署，HTTP 响应正常"
else
  echo "❌ 前端响应异常，请检查 nginx 日志"
  docker compose -f docker-compose.prod.yml logs nginx | tail -20
fi

echo ""
echo "=== 部署完成！==="
echo "前端地址: http://149.248.16.187/"
echo "API: http://149.248.16.187/api"
echo ""
echo "测试 KaTeX 公式渲染:"
echo "  1. 登录前端"
echo "  2. 进入「教学中心」"
echo "  3. 创建包含 LaTeX 公式的知识点（例如：$E=mc^2$ 或 $$\\frac{1}{2}$$）"
echo "  4. 验证公式渲染是否正确"
