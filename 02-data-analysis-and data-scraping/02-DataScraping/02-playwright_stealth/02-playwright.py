import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def test_both():
    # ── Test 1: WITHOUT stealth ──────────────────────────────
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://bot.sannysoft.com")
        await page.screenshot(path="1_WITHOUT_stealth.png", full_page=True)
        await browser.close()
        print("Test 1 done → 1_WITHOUT_stealth.png")

    # ── Test 2: WITH stealth ─────────────────────────────────
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await context.new_page()
        await page.goto("https://bot.sannysoft.com")
        await page.screenshot(path="2_WITH_stealth.png", full_page=True)
        await browser.close()
        print("Test 2 done → 2_WITH_stealth.png")

asyncio.run(test_both())