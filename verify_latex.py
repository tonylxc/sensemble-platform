#!/usr/bin/env python3
"""Verify KaTeX formulas in synced knowledge"""
import httpx
import asyncio
import json

async def main():
    api_base = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Login to get token
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

        token = resp.json().get("access_token")
        print(f"[+] Logged in successfully")

        # Get knowledge nodes with LaTeX formulas
        resp = await client.get(
            f"{api_base}/api/v1/teaching/nodes?course_code=EE-TEST-2026",
            headers={"Authorization": f"Bearer {token}"}
        )

        if resp.status_code != 200:
            print(f"[!] Get nodes failed: {resp.text}")
            return False

        nodes = resp.json()
        print(f"\n[+] Found {len(nodes)} knowledge points:")

        # Check each node for LaTeX formulas
        latex_count = 0
        for node in nodes:
            print(f"\n[*] Node: {node['title']}")
            content = node.get('content', '')

            # Count LaTeX formulas
            inline_count = content.count('$')  # Inline: $formula$
            display_count = content.count('$$')  # Display: $$formula$$

            if inline_count > 0 or display_count > 0:
                print(f"    [+] Contains LaTeX formulas:")
                print(f"        - Inline formulas ($ ... $): {inline_count // 2}")
                print(f"        - Display formulas ($$ ... $$): {display_count // 2}")
                latex_count += inline_count // 2 + display_count // 2

                # Show sample formulas
                import re
                formulas = re.findall(r'\$\$?[^\$]+\$\$?', content)
                for i, formula in enumerate(formulas[:3]):
                    print(f"        - Example {i+1}: {formula}")
            else:
                print(f"    [!] No LaTeX formulas found")

        print(f"\n[+] Total LaTeX formulas found: {latex_count}")
        print(f"[+] Ready for browser verification!")

        return True

if __name__ == "__main__":
    asyncio.run(main())
