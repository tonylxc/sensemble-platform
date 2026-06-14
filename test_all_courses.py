#!/usr/bin/env python3
"""Test if API returns all courses when course_code is empty"""
import httpx
import asyncio

async def main():
    api_base = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Login
        resp = await client.post(
            f"{api_base}/api/v1/auth/login",
            data={"username": "teacher_sync", "password": "test123456"}
        )
        token = resp.json().get("access_token")
        print(f"[+] 登录成功，Token: {token[:20]}...")

        # Test 1: Query with specific course code
        print("\n[*] 测试 1：查询特定课程 (EE-TEST-2026)")
        resp = await client.get(
            f"{api_base}/api/v1/teaching/nodes?course_code=EE-TEST-2026",
            headers={"Authorization": f"Bearer {token}"}
        )
        nodes_specific = resp.json()
        print(f"    返回知识点数：{len(nodes_specific)}")
        for node in nodes_specific:
            print(f"    - {node['title']} (course_code: {node.get('course_code', 'None')})")

        # Test 2: Query without course code (all courses)
        print("\n[*] 测试 2：查询所有课程（不指定 course_code）")
        resp = await client.get(
            f"{api_base}/api/v1/teaching/nodes",
            headers={"Authorization": f"Bearer {token}"}
        )
        nodes_all = resp.json()
        print(f"    返回知识点数：{len(nodes_all)}")
        for node in nodes_all:
            print(f"    - {node['title']} (course_code: {node.get('course_code', 'None')})")

        # Test 3: Query with empty course code
        print("\n[*] 测试 3：查询空课程代码（course_code=）")
        resp = await client.get(
            f"{api_base}/api/v1/teaching/nodes?course_code=",
            headers={"Authorization": f"Bearer {token}"}
        )
        nodes_empty = resp.json()
        print(f"    返回知识点数：{len(nodes_empty)}")
        for node in nodes_empty:
            print(f"    - {node['title']} (course_code: {node.get('course_code', 'None')})")

        # Summary
        print(f"\n[+] 总结：")
        print(f"    特定课程节点数：{len(nodes_specific)}")
        print(f"    无参数查询节点数：{len(nodes_all)}")
        print(f"    空参数查询节点数：{len(nodes_empty)}")

if __name__ == "__main__":
    asyncio.run(main())
