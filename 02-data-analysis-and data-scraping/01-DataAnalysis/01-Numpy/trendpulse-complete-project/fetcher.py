import aiohttp
import asyncio
import random
import logging

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
]

async def fetch_html(url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 403:
                raise PermissionError(f"403 Forbidden Error {url}")
            html = await response.text()
            return html


async def fetch_html_js(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        stealth = Stealth(init_scripts_only=True)
        await stealth.apply_stealth_async(page)
        await page.goto(url)
        await page.wait_for_selector("body")
        html = await page.content()
        await browser.close()
        return html


async def fetch_with_retry(url, max_tries=3):
    for attempt in range(max_tries):
        try:
            html = await fetch_html(url)
            return html
        except (PermissionError, asyncio.TimeoutError):
            raise
        except Exception:
            if attempt == max_tries - 1:
                raise
            wait_time = 2 * attempt
            await asyncio.sleep(wait_time)


async def fetch_with_fallback(url, max_tries=3):
    try:
        return await fetch_with_retry(url, max_tries)
    except (PermissionError, asyncio.TimeoutError) as e:
        logging.warning(f"Falling back to Playwright for {url}: {e}")
        return await fetch_html_js(url)
