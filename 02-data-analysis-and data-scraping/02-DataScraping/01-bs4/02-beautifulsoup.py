import asyncio
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import json
import hashlib
import os
from datetime import datetime

sites = [
    {"url": "https://httpbin.org/html", "css": "h1"},
    {"url": "https://example.com", "css": "h1"},
    {"url": "https://httpbin.org/html", "css": "p"},
]
ROUNDS = 3
WAIT_TIME = 10
MAX_WORKERS = 2
TIMEOUT = 6

old_values = {}

def get_time():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def make_filename(url):
    h = hashlib.sha256(url.encode()).hexdigest()
    return h[:10]

async def fetch_site(session, site, sem):
    async with sem:
        try:
            async with session.get(site["url"], timeout=TIMEOUT) as res:
                if res.status != 200:
                    return None, f"bad status {res.status}"
                html = await res.text()
                return html, None
        except asyncio.TimeoutError:
            return None, "timeout"
        except Exception as e:
            return None, str(e)

def parse_html(html, css_selector):
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(css_selector)
    if el is None:
        return None
    return el.get_text(strip=True)

async def process_site(session, site, sem, results):
    html, err = await fetch_site(session, site, sem)

    if err:
        print(f"error fetching {site['url']}: {err}")
        results.append({
            
            "url": site["url"],
            "value": None,
            "changed": False,
            "error": err,

            "time": get_time()
        })
        return

    text = parse_html(html, site["css"])

    if text is None:
        print(f"couldnt find {site['css']} on {site['url']}")
        results.append({
            "url": site["url"],
            "value": None,
            "changed": False,
            "error": "selector not found",
            "time": get_time()
        })
        return

    changed = False
    key = site["url"]  
    if key in old_values:
        if old_values[key] != text:
            changed = True
            print(f"CHANGED: {site['url']} -> {text}")
    old_values[key] = text

    result = {
        "url": site["url"],
        "value": text,
        "changed": changed,
        "error": None,
        "time": get_time()
    }
    results.append(result)

    fname = make_filename(site["url"]) + ".txt"
    path = os.path.join("snapshots", fname)

    async with aiofiles.open(path, "w") as f:
        await f.write(text)

    async with aiofiles.open("changes.jsonl", "a") as f:
        await f.write(json.dumps(result) + "\n")

    print(f"checked {site['url']} ok")

async def run_one_round(sites):
    sem = asyncio.Semaphore(MAX_WORKERS)
    results = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for site in sites:
            task = process_site(session, site, sem, results)
            tasks.append(task)

        await asyncio.gather(*tasks)

    return results

async def main():
    if not os.path.exists("snapshots"):
        os.mkdir("snapshots")

    all_results = []

    for i in range(ROUNDS):
        print(f"--- round {i+1} ---")
        res = await run_one_round(sites)
        all_results += res

        if i != ROUNDS - 1:
            print(f"waiting {WAIT_TIME} seconds...")
            await asyncio.sleep(WAIT_TIME)

    total_changes = 0
    for r in all_results:
        if r["changed"]:
            total_changes += 1

    print(f"\ndone! total checks: {len(all_results)}, changes: {total_changes}")

if __name__ == "__main__":
    asyncio.run(main())