from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import asyncio

async def fetch_js_html(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        stealth = Stealth(
        init_scripts_only=True
    )
        await stealth.apply_stealth_async(page)
        # apply stealth here — you have this import already, what's the method call?
        await page.goto(url)
        await page.wait_for_selector('.quote')
        # wait for real content — what method waits for a specific element to appear?
        html = await page.content()
        await browser.close()
        return html

async def main():
    html = await fetch_js_html("http://quotes.toscrape.com/js")
    print(html[:1000])

asyncio.run(main())