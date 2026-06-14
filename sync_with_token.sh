#!/bin/bash
# 获取 Token 并同步知识点

API_URL="http://localhost:8000"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin123"
COURSE_CODE="EE-TEST-2026"
KNOWLEDGE_DIR="docs/knowledge/"

echo "=========================================="
echo "获取 Token 并同步知识点"
echo "=========================================="
echo ""

# 1. 登录获取 Token
echo "[*] 正在登录 $ADMIN_USERNAME..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD")

echo "    响应: $TOKEN_RESPONSE"
echo ""

# 提取 access_token
TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "[!] 无法获取 Token"
    echo "    请检查:"
    echo "    1. API 服务是否运行 (curl $API_URL/docs)"
    echo "    2. Admin 凭证是否正确 (admin/admin123)"
    exit 1
fi

echo "[+] 成功获取 Token!"
echo "    Token: ${TOKEN:0:30}..."
echo ""

# 2. 运行同步脚本
echo "[*] 开始同步知识点..."
echo "    目录: $KNOWLEDGE_DIR"
echo "    课程: $COURSE_CODE"
echo ""

python3 tools/sync_knowledge.py \
  --dir "$KNOWLEDGE_DIR" \
  --course "$COURSE_CODE" \
  --api "$API_URL" \
  --token "$TOKEN"

echo ""
echo "[+] 同步完成!"
