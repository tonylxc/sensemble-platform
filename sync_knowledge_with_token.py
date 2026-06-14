#!/usr/bin/env python3
"""
获取 JWT Token 并同步知识点
"""
import httpx
import asyncio
import sys
import subprocess

async def get_token(api_url, username, password):
    """登录获取 JWT Token"""
    async with httpx.AsyncClient() as client:
        print(f"[*] 正在登录 {username}...")
        try:
            resp = await client.post(
                f"{api_url}/api/v1/auth/login",
                data={"username": username, "password": password}
            )

            if resp.status_code != 200:
                print(f"[!] 登录失败: {resp.status_code}")
                print(f"    错误: {resp.text}")
                return None

            data = resp.json()
            token = data.get("access_token")
            role = data.get("role")

            if token:
                print(f"[✓] 登录成功!")
                print(f"    用户: {username}")
                print(f"    角色: {role}")
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
    knowledge_dir = "docs/knowledge/"

    print("=" * 60)
    print("Sensemble 知识点同步工具")
    print("=" * 60)
    print()

    # 第一步：获取 Token
    token = await get_token(api_url, admin_username, admin_password)

    if not token:
        print("[!] 无法获取 Token，同步失败")
        sys.exit(1)

    print()

    # 第二步：运行同步脚本
    print(f"[*] 开始同步知识点...")
    print(f"    目录: {knowledge_dir}")
    print(f"    课程: {course_code}")
    print(f"    API: {api_url}")
    print()

    cmd = [
        sys.executable, "tools/sync_knowledge.py",
        "--dir", knowledge_dir,
        "--course", course_code,
        "--api", api_url,
        "--token", token
    ]

    print(f"[*] 执行命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)

    print()
    if result.returncode == 0:
        print("=" * 60)
        print("[✓] 同步完成!")
        print("=" * 60)
    else:
        print("[!] 同步失败，请检查日志")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
