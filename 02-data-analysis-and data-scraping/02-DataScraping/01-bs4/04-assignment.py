from __future__ import annotations
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles
import aiohttp
from bs4 import BeautifulSoup

SITES = [
    {"url": "https://httpbin.org/html",  "css": "h1"},
    {"url": "https://example.com",       "css": "h1"},
    {"url": "https://httpbin.org/html",  "css": "p"}, 
]

TOTAL_ROUNDS   = 3
SLEEP_BETWEEN  = 10  
MAX_CONCURRENT = 2 
TIMEOUT_SEC    = 6
MAX_RETRIES    = 1

SNAPSHOTS_DIR  = Path("snapshots")
CHANGES_FILE   = Path("changes.jsonl")

@dataclass
class Site:
    url: str
    css: str

@dataclass
class Result:
    url:           str
    css:           str
    timestamp:     str
    current_value: Optional[str]
    changed:       bool
    error:         Optional[str]

    def to_dict(self) -> dict:
        return {
            "url":           self.url,
            "css":           self.css,
            "timestamp":     self.timestamp,
            "current_value": self.current_value,
            "changed":       self.changed,
            "error":         self.error,
        }

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:10]

def bootstrap() -> None:
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    if not CHANGES_FILE.exists():
        CHANGES_FILE.touch()

async def fetch(session: aiohttp.ClientSession,
                site: Site,
                semaphore: asyncio.Semaphore) -> tuple[Site, Optional[str], Optional[str]]:
    """
    Returns (site, html, error).
    Acquires semaphore here — the semaphore is the unit of concurrency.
    Retries once on any failure after a 2s wait.
    """
    async with semaphore:
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            if attempt > 0:
                await asyncio.sleep(2)      
                print(f"    [retry] {site.url}")

            try:
                timeout = aiohttp.ClientTimeout(total=TIMEOUT_SEC)
                async with session.get(site.url, timeout=timeout,
                                       raise_for_status=True) as resp:
                    html = await resp.text()
                    return site, html, None    

            except aiohttp.ClientResponseError as e:
                last_error = f"HTTP {e.status}"
            except asyncio.TimeoutError:
                last_error = "TimeoutError"
            except aiohttp.ClientConnectionError as e:
                last_error = f"ConnectionError: {e}"
            except Exception as e:
                last_error = f"UnexpectedError: {e}"

        return site, None, last_error           

def parse(site: Site, html: Optional[str],
          fetch_error: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Synchronous — BS4 is CPU-bound.
    Called via run_in_executor in the worker so it never blocks the event loop.
    Returns (text, error).
    """
    if fetch_error:
        return None, "SkippedFetchError"
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception as e:
        return None, f"ParseError: {e}"
    
    element = soup.select_one(site.css)
    if element is None:
        return None, "SelectorNotFound"

    text = " ".join(element.get_text(separator=" ", strip=True).split())
    return text, None

def detect(site: Site,
           text: Optional[str],
           error: Optional[str],
           state: Dict[str, Optional[str]]) -> Result:
    """
    Compares current text against state dict.
    Never updates state on error — transient failures must not reset the baseline.
    """
    ts = utc_now()

    if error:
        return Result(url=site.url, css=site.css, timestamp=ts,
                      current_value=None, changed=False, error=error)

    previous = state.get(site.url)

    if previous is None:
        changed = False       
    else:
        changed = (text.strip() != previous.strip())

    state[site.url] = text         

    return Result(url=site.url, css=site.css, timestamp=ts,
                  current_value=text, changed=changed, error=None)

_jsonl_lock = asyncio.Lock()    

async def write_snapshot(result: Result) -> None:
    """Only writes on successful parse — no empty files for errors."""
    if result.current_value is None:
        return

    ts_safe  = result.timestamp.replace(":", "-")
    filename = f"{url_hash(result.url)}_{ts_safe}.txt"
    filepath = SNAPSHOTS_DIR / filename

    async with aiofiles.open(filepath, mode="w", encoding="utf-8") as f:
        await f.write(result.current_value)

async def append_jsonl(result: Result) -> None:
    line = json.dumps(result.to_dict(), ensure_ascii=False) + "\n"
    async with _jsonl_lock:
        async with aiofiles.open(CHANGES_FILE, mode="a", encoding="utf-8") as f:
            await f.write(line)

async def write_result(result: Result) -> None:
    """Run both writers concurrently — they touch different files."""
    await asyncio.gather(write_snapshot(result), append_jsonl(result))

async def worker(session:   aiohttp.ClientSession,
                 semaphore: asyncio.Semaphore,
                 queue:     asyncio.Queue,
                 state:     Dict[str, Optional[str]],
                 results:   List[Result]) -> None:
    """
    Pulls sites from queue until it sees the sentinel (None).
    Runs the full pipeline: fetch → parse → detect → write.
    BS4 parse goes through run_in_executor so it never freezes the event loop.
    """
    loop = asyncio.get_running_loop()

    while True:
        site = await queue.get()

        if site is None:                 
            queue.task_done()
            return

        try:
            site_obj, html, fetch_err = await fetch(session, site, semaphore)

            text, parse_err = await loop.run_in_executor(
                None, parse, site_obj, html, fetch_err
            )
            result = detect(site_obj, text, parse_err, state)

            await write_result(result)

            results.append(result)

            tag = "CHANGED" if result.changed else ("ERR" if result.error else " ok ")
            print(f"  [{tag}]  {site.url}  css={site.css!r}"
                  + (f"  → {result.current_value!r}" if result.current_value else
                     f"  error={result.error}"))

        except Exception as e:
            print(f"  [worker crash] {site.url}: {e}")

        finally:
            queue.task_done()

async def run_round(session:   aiohttp.ClientSession,semaphore: asyncio.Semaphore,
                    sites:     List[Site],state:     Dict[str, Optional[str]]) -> List[Result]:
    """
    One sweep across all sites using Queue + sentinel pattern.
    MAX_CONCURRENT workers drain the queue concurrently.
    """
    queue: asyncio.Queue = asyncio.Queue()

    for site in sites:
        await queue.put(site)

    for _ in range(MAX_CONCURRENT):
        await queue.put(None)
    results: List[Result] = []

    workers = [
        asyncio.create_task(worker(session, semaphore, queue, state, results))
        for _ in range(MAX_CONCURRENT)
    ]

    await asyncio.gather(*workers)
    return results

async def run_monitor(sites: List[Site]) -> None:
    """Outer loop: TOTAL_ROUNDS rounds with SLEEP_BETWEEN seconds between each."""
    state:     Dict[str, Optional[str]] = {s.url: None for s in sites}
    semaphore: asyncio.Semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    all_results: List[Result]   = []

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:

        for round_num in range(1, TOTAL_ROUNDS + 1):
            print(f"\n{'─'*50}")
            print(f" Round {round_num}/{TOTAL_ROUNDS}")
            print(f"{'─'*50}")

            round_results = await run_round(session, semaphore, sites, state)
            all_results.extend(round_results)

            if round_num < TOTAL_ROUNDS:
                print(f"\n  sleeping {SLEEP_BETWEEN}s before next round …")
                await asyncio.sleep(SLEEP_BETWEEN)

    print_summary(all_results)

def print_summary(results: List[Result]) -> None:
    total   = len(results)
    changed = sum(1 for r in results if r.changed)
    errors  = sum(1 for r in results if r.error)
    urls    = sorted(set(r.url for r in results))

    change_counts: Dict[str, int] = {}
    for r in results:
        if r.changed:
            change_counts[r.url] = change_counts.get(r.url, 0) + 1

    print(f"\n{'═'*50}")
    print("  SUMMARY")
    print(f"{'═'*50}")
    print(f"  URLs monitored  : {len(urls)}")
    print(f"  Total checks    : {total}")
    print(f"  Total changes   : {changed}")
    print(f"  Total errors    : {errors}")

    if change_counts:
        print("\n  URLs that changed:")
        for url, count in sorted(change_counts.items(), key=lambda x: -x[1]):
            print(f"    {count}x  {url}")
    else:
        print("\n  No changes detected.")
    print(f"{'═'*50}")

async def main() -> None:
    bootstrap()

    sites = [Site(url=s["url"], css=s["css"]) for s in SITES]

    print(f"[monitor] {len(sites)} sites  |  {TOTAL_ROUNDS} rounds  "
          f"|  Semaphore({MAX_CONCURRENT})  |  {SLEEP_BETWEEN}s between rounds")

    await run_monitor(sites)

if __name__ == "__main__":
    asyncio.run(main())