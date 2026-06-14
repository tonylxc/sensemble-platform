#!/usr/bin/env python3
"""Helper script to register teacher, get token, and sync knowledge"""
import httpx
import asyncio
import sys

async def main():
    api_base = "http://localhost:8000"

    # 1. Register teacher account
    print("[*] Registering teacher account...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/v1/auth/register",
            json={
                "username": "teacher_sync",
                "email": "teacher@test.com",
                "password": "test123456",
                "role": "teacher"
            }
        )
        if resp.status_code != 200:
            print(f"[!] Register failed: {resp.text}")
            # Try login instead
            resp = await client.post(
                f"{api_base}/api/v1/auth/login",
                data={
                    "username": "teacher_sync",
                    "password": "test123456"
                }
            )
            if resp.status_code != 200:
                print(f"[!] Login failed: {resp.text}")
                return False

        data = resp.json()
        token = data.get("access_token")
        print(f"[+] Got Token: {token[:20]}...")

        # 2. Run the sync command with token
        print("\n[*] Syncing knowledge...")
        import subprocess
        cmd = [
            sys.executable, "tools/sync_knowledge.py",
            "--dir", "docs/knowledge/ch1/",
            "--course", "EE-TEST-2026",
            "--api", "http://localhost:8000",
            "--token", token
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
