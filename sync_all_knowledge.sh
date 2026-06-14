#!/bin/bash
# 递归同步 docs/knowledge/ 下的所有知识点

API_URL="http://localhost:8000"
COURSE_CODE="EE-TEST-2026"
KNOWLEDGE_ROOT="docs/knowledge"

echo "=========================================="
echo "批量同步所有知识点"
echo "=========================================="
echo ""

# 第一步：获取 Token
echo "[*] 获取认证 Token..."
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "[!] Token 获取失败"
    exit 1
fi

echo "[+] Token 获取成功"
echo ""

# 第二步：找到所有包含 .md 文件的目录
echo "[*] 扫描 $KNOWLEDGE_ROOT 下的所有目录..."
DIRS=$(find "$KNOWLEDGE_ROOT" -type d | sort)

TOTAL_DIRS=0
TOTAL_CREATED=0
TOTAL_UPDATED=0
TOTAL_FAILED=0

for dir in $DIRS; do
    # 跳过根目录本身和空目录
    if [ "$dir" = "$KNOWLEDGE_ROOT" ]; then
        continue
    fi

    # 检查目录下是否有 .md 文件
    MD_COUNT=$(find "$dir" -maxdepth 1 -name "*.md" -type f | wc -l)

    if [ $MD_COUNT -gt 0 ]; then
        TOTAL_DIRS=$((TOTAL_DIRS + 1))

        echo ""
        echo "─────────────────────────────────────"
        echo "[$TOTAL_DIRS] 同步目录：$dir ($MD_COUNT 个文件)"
        echo "─────────────────────────────────────"

        # 运行同步
        python3 tools/sync_knowledge.py \
            --dir "$dir" \
            --course "$COURSE_CODE" \
            --api "$API_URL" \
            --token "$TOKEN" 2>&1 | tail -5

        # 提取统计信息（简单的计数）
        # 你也可以解析输出来获取更详细的统计
    fi
done

echo ""
echo "=========================================="
echo "[+] 全部同步完成!"
echo "    处理目录数：$TOTAL_DIRS"
echo "    课程代码：$COURSE_CODE"
echo "=========================================="
echo ""
echo "[*] 验证同步结果..."
echo "    访问前端：http://149.248.16.187:8080"
echo "    进入教学中心查看所有知识点"
