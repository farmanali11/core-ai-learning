#!/usr/bin/env python3
"""
UK Postcode Demographics Pipeline
==================================
Stack   : asyncio + aiohttp (async HTTP, no browser needed — this is a clean JSON API)
Source  : postcodes.io  -> https://api.postcodes.io  (free, public, bulk endpoint, no auth, no rate-limit)
          ONS Postcode Directory (ONSPD) data under Open Government Licence v3.0

Why no Playwright / Scrapling / proxies here:
    postcodes.io is a plain JSON REST API explicitly designed for bulk programmatic
    lookups (its own docs advertise a /postcodes bulk endpoint, up to 100 codes per
    call). There's no JS rendering, no anti-bot layer, and no daily-view cap to work
    around, so a browser-automation stack would just add overhead for nothing. The
    async/retry/backoff/CSV architecture you were building is preserved 1:1 — it's
    just pointed at a target that wants to be hit at scale instead of one that
    rate-limits free use.

Demographic-style fields captured (>=5 categories, all real ONSPD/Census-linked data):
    1. Index of Multiple Deprivation (IMD) rank  -> socioeconomic deprivation
    2. Region / Admin district / Admin ward      -> local governance geography
    3. Population-relevant census geography (LSOA, MSOA, Output Area linkage)
    4. NHS Health Authority / CCG / ICB           -> health geography
    5. Parliamentary constituency                 -> electoral geography
    6. Rural/urban classification (built-up area) -> settlement type
    7. Police Force Area                          -> public safety geography

Run:
    pip install aiohttp --break-system-packages
    python scraper.py
"""

import asyncio
import csv
import logging
import sys
from dataclasses import dataclass, asdict, fields
from typing import Optional, Any

import aiohttp

# ── Force UTF-8 console output (fixes the cp1252 UnicodeEncodeError from before) ──
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Config ───────────────────────────────────────────────────────────────────
API_BASE         = "https://api.postcodes.io"
BULK_ENDPOINT    = f"{API_BASE}/postcodes"
RANDOM_ENDPOINT  = f"{API_BASE}/random/postcodes"
BULK_CHUNK_SIZE  = 100          # API hard limit per request
CONCURRENCY      = 5            # simultaneous in-flight requests
RETRIES          = 3
BACKOFF_BASE     = 1.5          # seconds, exponential backoff base
OUTPUT_CSV       = "uk_postcode_demographics.csv"
REQUEST_TIMEOUT  = 15           # seconds
TARGET_COUNT     = 20           # how many England postcodes we want

# Hand-typed postcodes are easy to get subtly wrong (an outward code doesn't
# necessarily pair with every inward code you'd guess, e.g. "RG1 1AA" might
# not exist even though "RG1" and "1AA"-style codes both look plausible).
# Instead of hardcoding 20 postcodes, we ask postcodes.io's own
# /random/postcodes endpoint for real, currently-valid postcodes, then keep
# pulling until we have 20 distinct ones in England. This guarantees every
# postcode we send to the bulk endpoint actually exists in the ONS directory.
async def fetch_random_england_postcodes(
    session: aiohttp.ClientSession, count: int
) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = count * 5  # safety valve against an unlikely infinite loop

    while len(collected) < count and attempts < max_attempts:
        attempts += 1
        async with session.get(
            RANDOM_ENDPOINT, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                continue
            data = await resp.json()
            result = data.get("result")
            if not result:
                continue
            postcode = result.get("postcode")
            country = result.get("country")
            if postcode and country == "England" and postcode not in seen:
                seen.add(postcode)
                collected.append(postcode)
                log.info(f"Discovered valid England postcode: {postcode}")

    return collected


# ── Data Model ───────────────────────────────────────────────────────────────
@dataclass
class PostcodeDemographics:
    postcode: str
    status: str = "pending"
    error: Optional[str] = None

    # Core geography
    country: Optional[str] = None
    region: Optional[str] = None
    admin_district: Optional[str] = None
    admin_county: Optional[str] = None
    admin_ward: Optional[str] = None
    parish: Optional[str] = None

    # Census statistical geography (links to ONS Census 2021 output areas)
    lsoa: Optional[str] = None          # Lower Layer Super Output Area
    msoa: Optional[str] = None          # Middle Layer Super Output Area

    # Socioeconomic / deprivation
    index_of_multiple_deprivation: Optional[Any] = None  # IMD rank (England)

    # Electoral
    parliamentary_constituency: Optional[str] = None
    european_electoral_region: Optional[str] = None

    # Health geography
    nhs_health_authority: Optional[str] = None
    ccg: Optional[str] = None           # Clinical Commissioning Group
    primary_care_trust: Optional[str] = None

    # Settlement / urbanity
    built_up_area: Optional[str] = None
    travel_to_work_area: Optional[str] = None

    # Public safety geography
    police_force_area: Optional[str] = None

    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None


FIELDNAMES = [f.name for f in fields(PostcodeDemographics)]


# ── API key -> dataclass field mapping (postcodes.io response field names) ───
FIELD_MAP = {
    "country":                       "country",
    "region":                        "region",
    "admin_district":                "admin_district",
    "admin_county":                  "admin_county",
    "admin_ward":                    "admin_ward",
    "parish":                        "parish",
    "lsoa":                          "lsoa",
    "msoa":                          "msoa",
    "index_of_multiple_deprivation": "index_of_multiple_deprivation",
    "parliamentary_constituency":     "parliamentary_constituency",
    "european_electoral_region":     "european_electoral_region",
    "nhs_ha":                        "nhs_health_authority",
    "ccg":                           "ccg",
    "primary_care_trust":            "primary_care_trust",
    "bua":                           "built_up_area",
    "ttwa":                          "travel_to_work_area",
    "pfa":                           "police_force_area",
    "latitude":                      "latitude",
    "longitude":                     "longitude",
}


def parse_result(raw: dict, postcode: str) -> PostcodeDemographics:
    """Map a single postcodes.io result object onto our dataclass."""
    record = PostcodeDemographics(postcode=postcode, status="ok")
    for api_key, field_name in FIELD_MAP.items():
        value = raw.get(api_key)
        # postcodes.io uses "" for some unset string fields; normalize to None
        if value == "":
            value = None
        setattr(record, field_name, value)
    return record


# ── Async fetch with retry/backoff ────────────────────────────────────────────
async def fetch_bulk_chunk(
    session: aiohttp.ClientSession,
    chunk: list[str],
    semaphore: asyncio.Semaphore,
) -> list[PostcodeDemographics]:
    """
    POSTs one chunk (<=100 postcodes) to the bulk endpoint, with retry/backoff.
    Returns one PostcodeDemographics record per input postcode, including
    failed/not-found ones, so the output CSV always has a row per requested code.
    """
    payload = {"postcodes": chunk}

    async with semaphore:
        for attempt in range(1, RETRIES + 1):
            try:
                log.info(f"[{attempt}/{RETRIES}] POST {BULK_ENDPOINT} for {len(chunk)} postcodes")
                async with session.post(
                    BULK_ENDPOINT,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ) as resp:

                    if resp.status == 429:
                        wait = BACKOFF_BASE * (2 ** attempt)
                        log.warning(f"429 rate-limited — backing off {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status >= 500:
                        wait = BACKOFF_BASE * (2 ** attempt)
                        log.warning(f"Server error {resp.status} — retrying in {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status != 200:
                        body = await resp.text()
                        raise ValueError(f"Unexpected status {resp.status}: {body[:200]}")

                    payload_json = await resp.json()
                    results = payload_json.get("result", [])

                    out: list[PostcodeDemographics] = []
                    for item in results:
                        query = item.get("query", "")
                        result_obj = item.get("result")
                        if result_obj is None:
                            out.append(PostcodeDemographics(
                                postcode=query,
                                status="not_found",
                                error="No match in ONS Postcode Directory",
                            ))
                        else:
                            out.append(parse_result(result_obj, query))

                    log.info(f"✓ Chunk OK — {len(out)} records parsed")
                    return out

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                log.error(f"Attempt {attempt} failed: {exc!r}")
                if attempt < RETRIES:
                    backoff = BACKOFF_BASE * (2 ** attempt)
                    log.info(f"Backing off {backoff:.1f}s before retry")
                    await asyncio.sleep(backoff)

        # All retries exhausted — mark every postcode in this chunk as failed
        log.error(f"Chunk failed after {RETRIES} attempts: {chunk}")
        return [
            PostcodeDemographics(postcode=pc, status="failed", error="Max retries exceeded")
            for pc in chunk
        ]


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


# ── CSV writer ────────────────────────────────────────────────────────────────
def write_csv(records: list[PostcodeDemographics], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    log.info(f"CSV written -> {path} ({len(records)} rows)")


# ── Main ──────────────────────────────────────────────────────────────────────
async def main() -> None:
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(
        headers={"User-Agent": "uk-postcode-demographics-pipeline/1.0"}
    ) as session:

        log.info(f"Discovering {TARGET_COUNT} valid England postcodes via /random/postcodes ...")
        postcodes = await fetch_random_england_postcodes(session, TARGET_COUNT)

        if len(postcodes) < TARGET_COUNT:
            log.warning(
                f"Only found {len(postcodes)}/{TARGET_COUNT} postcodes after retry budget — "
                f"continuing with what we have"
            )

        chunks = chunked(postcodes, BULK_CHUNK_SIZE)  # 20 postcodes -> 1 chunk, but scales to 100s
        log.info(f"Fetching demographics for {len(postcodes)} postcodes across {len(chunks)} chunk(s)")

        tasks = [fetch_bulk_chunk(session, chunk, semaphore) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks)

    all_records: list[PostcodeDemographics] = [r for chunk in chunk_results for r in chunk]

    write_csv(all_records, OUTPUT_CSV)

    ok = sum(1 for r in all_records if r.status == "ok")
    not_found = sum(1 for r in all_records if r.status == "not_found")
    failed = sum(1 for r in all_records if r.status == "failed")

    log.info("=" * 55)
    log.info(f"COMPLETE: {ok} ok / {not_found} not_found / {failed} failed")
    log.info(f"Output  : {OUTPUT_CSV}")
    log.info("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())