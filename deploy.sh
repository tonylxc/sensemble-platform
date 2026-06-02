#!/usr/bin/env bash
# 众感 Sensemble 一键部署（Ubuntu 22.04，以 root 在仓库根目录运行）
set -euo pipefail
cd "$(dirname "$0")"

echo "==> [1/5] 安装 Docker（已装则跳过）"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || { echo "需要 docker compose v2，请检查 Docker 安装"; exit 1; }

echo "==> [2/5] 生成 .env（强随机密钥，仅首次）"
if [ ! -f .env ]; then
  g() { openssl rand -hex 24; }
  SECRET=$(g); DBPASS=$(g); ADMINPASS=$(openssl rand -hex 8)
  MQTTPASS=$(g); MQTTSECRET=$(g); MINIOPASS=$(g); GRAFPASS=$(openssl rand -hex 8)
  cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMINPASS}
CORS_ORIGINS=*
DB_HOST=db
DB_PORT=5432
DB_USER=sensemble
DB_PASSWORD=${DBPASS}
DB_NAME=sensemble
MQTT_HOST=emqx
MQTT_PORT=1883
MQTT_TOPIC=sensemble/+/data
MQTT_ENABLED=true
MQTT_BACKEND_USER=backend-ingest
MQTT_BACKEND_PASSWORD=${MQTTPASS}
MQTT_AUTH_SECRET=${MQTTSECRET}
MINIO_ENDPOINT=minio:9000
MINIO_USER=minioadmin
MINIO_PASSWORD=${MINIOPASS}
GRAFANA_PASSWORD=${GRAFPASS}
EOF
  # 让 EMQX 回调密钥与 .env 一致
  sed -i "s/change-me-internal/${MQTTSECRET}/g" emqx/emqx.conf
  echo "    .env 已生成。管理员：admin / ${ADMINPASS}   <<< 请记下这个密码"
else
  echo "    .env 已存在，跳过生成"
fi

echo "==> [3/5] 防火墙放行 22/80/443/8000/1883"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw allow 8000/tcp || true
  ufw allow 1883/tcp || true
  yes | ufw enable || true
fi

echo "==> [4/5] 构建并启动（首次约 3-8 分钟）"
docker compose -f docker-compose.prod.yml up -d --build

echo "==> [5/5] 启动状态："
sleep 8
docker compose -f docker-compose.prod.yml ps
IP=$(curl -s --max-time 5 ifconfig.me || echo "<服务器IP>")
cat <<EOF

============================================================
 部署完成 🎉
   前端 Web     : http://${IP}/
   API/Swagger  : http://${IP}:8000/docs
   设备 MQTT    : ${IP}:1883   (username=设备ID, password=设备Token)
   管理员账号   : admin / <见上方 [2/5] 输出，或 cat .env>
 造数演示(可选) : apt-get install -y python3-pip && pip3 install -r tools/requirements.txt && python3 tools/simulate.py
============================================================
EOF
