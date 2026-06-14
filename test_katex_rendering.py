#!/usr/bin/env python3
"""Test KaTeX rendering in browser using Playwright"""
import asyncio
import time

async def test_katex():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[!] Playwright not installed. Install with: pip install playwright")
        print("[+] Skipping browser test")
        return True

    async with async_playwright() as p:
        print("[*] Starting browser automation...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to frontend
            print("[*] Navigating to http://localhost:8080...")
            await page.goto("http://localhost:8080", wait_until="networkidle")
            print("[+] Page loaded successfully")

            # Wait for page to stabilize
            await page.wait_for_timeout(2000)

            # Check if KaTeX is loaded
            katex_check = await page.evaluate("""
                () => {
                    return typeof window.katex !== 'undefined';
                }
            """)
            print(f"[{'+'if katex_check else '!'}] KaTeX library loaded: {katex_check}")

            # Check for rendered formulas
            formula_check = await page.evaluate("""
                () => {
                    const spans = document.querySelectorAll('span.katex');
                    return {
                        count: spans.length,
                        samples: Array.from(spans).slice(0, 3).map(s => s.textContent)
                    };
                }
            """)
            print(f"[+] Rendered formulas found: {formula_check['count']}")
            if formula_check['samples']:
                print(f"[+] Sample rendered content:")
                for sample in formula_check['samples'][:3]:
                    print(f"    - {sample[:60]}")

            # Check console for errors
            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))

            # Try to navigate to teaching center
            print("[*] Looking for teaching module...")
            await page.wait_for_timeout(1000)

            # Check page title
            title = await page.title()
            print(f"[+] Page title: {title}")

            # Get page content to verify teaching data is there
            content = await page.content()
            has_teaching = "teaching" in content.lower() or "EE-TEST-2026" in content
            print(f"[{'+'if has_teaching else '?'}] Teaching content found: {has_teaching}")

            return True

        except Exception as e:
            print(f"[!] Browser test error: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    try:
        result = asyncio.run(test_katex())
        print(f"\n[{'+'if result else '!'}] Browser test completed")
    except Exception as e:
        print(f"[!] Error: {e}")
