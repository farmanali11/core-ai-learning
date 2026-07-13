import aiohttp
import asyncio

import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
]


async def fetch_html(url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            print("Status", response.status)
            html = await response.text()
            return html
