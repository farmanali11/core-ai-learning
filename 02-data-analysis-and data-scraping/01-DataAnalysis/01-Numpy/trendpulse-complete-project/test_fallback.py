import asyncio
import logging
from fetcher import fetch_with_fallback

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
async def main():
    test_urls = [
        "https://www.radio.gov.pk/newslist/1",
        "https://www.bbc.com/news",
        "https://www.dawn.com/latest-news",
    ]
    for url in test_urls:
        print(f"\n--- Testing: {url} ---")
        try:
            html = await fetch_with_fallback(url)
            print(f"Success. HTML length: {len(html)} characters")
        except Exception as e:
            print(f"Failed entirely: {e}")
asyncio.run(main())
