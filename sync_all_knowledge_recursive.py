#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量同步所有知识点到后端（支持递归扫描）"""

import asyncio
import httpx
import json
import subprocess
import sys
from pathlib import Path

async def get_token(api_url: str, username: str, password: str) -> str:
    """获取 JWT Token"""
    print(f"[*] 正在登录 {username}...")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{api_url}/api/v1/auth/login",
                data={"username": username, "password": password},
                timeout=10.0
            )

            if resp.status_code != 200:
                print(f"[!] 登录失败: {resp.status_code}")
                print(f"    错误: {resp.text}")
                return None

            data = resp.json()
            token = data.get("access_token")

            if token:
                print(f"[✓] 登录成功!")
                print(f"    用户: {username}")
                print(f"    Token: {token[:30]}...")
                return token
            else:
                print(f"[!] 响应中没有 access_token")
                return None

        except Exception as e:
            print(f"[!] 错误: {e}")
            return None

async def main():
    # 配置
    api_url = "http://localhost:8000"
    admin_username = "admin"
    admin_password = "admin123"
    course_code = "EE-TEST-2026"
    knowledge_root = Path("docs/knowledge")

    print("=" * 70)
    print("Sensemble 知识点批量同步工具（递归版）")
    print("=" * 70)
    print()

    # 检查目录
    if not knowledge_root.is_dir():
        print(f"[!] 目录不存在：{knowledge_root}")
        sys.exit(1)

    # 获取 Token
    token = await get_token(api_url, admin_username, admin_password)

    if not token:
        print("[!] 无法获取 Token，同步失败")
        sys.exit(1)

    print()
    print("[*] 开始同步知识点...")
    print(f"    根目录: {knowledge_root}")
    print(f"    课程代码: {course_code}")
    print(f"    API 地址: {api_url}")
    print()

    # 运行同步脚本（递归扫描所有文件）
    cmd = [
        sys.executable, "tools/sync_knowledge.py",
        "--dir", str(knowledge_root),
        "--course", course_code,
        "--api", api_url,
        "--token", token
    ]

    print(f"[*] 执行命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    print()
    if result.returncode == 0:
        print("=" * 70)
        print("[✓] 同步完成！")
        print("=" * 70)
    else:
        print("[!] 同步失败，请检查日志")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
