import asyncio
import csv
import logging
import random
import sys
from dataclasses import dataclass, asdict, fields as dc_fields
from typing import Optional

import aiohttp
from scrapling.fetchers import AsyncStealthySession

# ── UTF-8 on Windows ────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════
PROXY_SERVER   = "http://gb.decodo.com:30000"
PROXY_USER     = "sp1tfuq8ld"
PROXY_PASSWORD = "i~kBmigi03GkkmT4O7"
PROXY_URL      = f"http://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_SERVER.split('://')[1]}"

HEADLESS        = True
PAGE_DELAY_MIN  = 4.0
PAGE_DELAY_MAX  = 9.0
READ_PAUSE_MIN  = 2.0
READ_PAUSE_MAX  = 5.0
PAGE_TIMEOUT_S  = 40
MAX_RETRIES     = 3
BACKOFF_BASE    = 2.0
OUTPUT_CSV      = "postcode_demographics.csv"
LOG_FILE        = "scraper.log"

CONTENT_SELECTOR = "div.headlineNumber, h3.headlineNumber, span.sc-value"

POSTCODES: list[str] = [
    "SW1A 1AA", "M1 1AE", "B1 1BB", "LS1 1BA", "E1 6RF",
    "BS1 10AA", "NE1 4ST", "S1 2BJ", "L1 8JQ", "NG1 1GF",
    "OX1 1PT", "CB2 1TN", "CV1 1GF", "LE1 1SH", "PL11 2AA",
    "SO14 0YG", "RG1 1EH", "MK9 1EN", "YO1 9SB", "EX1 1GE",
]

# ══════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class PostcodeDemographics:
    postcode:            str
    status:              str           = "pending"
    error:               Optional[str] = None
    scraped_url:         Optional[str] = None

    population_total:    Optional[str] = None
    population_density:  Optional[str] = None
    households:          Optional[str] = None
    household_income:    Optional[str] = None

    ab_social_score:      Optional[str] = None
    education_score:      Optional[str] = None
    credit_status_score:  Optional[str] = None


FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]


# ══════════════════════════════════════════════════════════════════════════
#  PARSER — Scrapling's Adaptor supports adaptive relocation, so selectors
#  survive site redesigns automatically (auto_save on first run, adaptive
#  on subsequent runs). Ancestor lookups use xpath instead of manual
#  BeautifulSoup find_parent() walking.
# ══════════════════════════════════════════════════════════════════════════
def parse_demographics(page, postcode: str, url: str) -> PostcodeDemographics:
    rec = PostcodeDemographics(postcode=postcode, status="ok", scraped_url=url)

    def clean(txt: Optional[str]) -> Optional[str]:
        if txt is None:
            return None
        return txt.replace(",", "").replace("£", "").strip()

    def card_value(xpath_probe: str) -> Optional[str]:
        """xpath_probe must locate the trigger element (img/h2/h3); we then
        climb to the nearest ancestor .card and pull .headlineNumber."""
        el = page.xpath(f"({xpath_probe})[1]/ancestor::div[contains(@class,'card')][1]", adaptive=True)
        if not el:
            return None
        val = el[0].css_first(".headlineNumber::text", adaptive=True)
        return clean(val) if val else None

    def score_card(heading_text: str) -> Optional[str]:
        el = page.xpath(
            f"//h3[contains(@class,'h3')][normalize-space(text())='{heading_text}']"
            f"/ancestor::div[contains(@class,'card')][1]",
            adaptive=True,
        )
        if not el:
            return None
        val = el[0].css_first("span.sc-value::text", adaptive=True)
        return val.strip() if val else None

    # ── Layer 1 — stat cards ────────────────────────────────────────────
    rec.population_total = card_value(
        "//img[contains(@src,'icons/population.png')] | //img[contains(translate(@alt,'P','p'),'population')]"
    )
    rec.population_density = card_value(
        "//img[contains(@src,'icons/population_density.png')] | //img[contains(@alt,'Population Density')]"
    )
    rec.households = card_value("//h2[contains(@class,'h3')][contains(text(),'Households')]")
    hh_income = card_value("//h2[contains(@class,'h3')][contains(text(),'Household Income')]")
    rec.household_income = clean(hh_income)

    # ── Layer 2 — gauge scores ───────────────────────────────────────────
    rec.ab_social_score     = score_card("AB Social Score")
    rec.education_score     = score_card("Education Score")
    rec.credit_status_score = score_card("Credit Status Score")

    return rec


# ══════════════════════════════════════════════════════════════════════════
#  URL RESOLVER — postcodes.io → postcodearea.co.uk slug
#  (kept as-is; see note above about why it wasn't dropped)
# ══════════════════════════════════════════════════════════════════════════
async def resolve_url(session: aiohttp.ClientSession, postcode: str) -> Optional[str]:
    import re
    clean = postcode.replace(" ", "").upper()
    try:
        async with session.get(
            f"https://api.postcodes.io/postcodes/{clean}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status != 200:
                log.warning(f"postcodes.io {r.status} for {postcode}")
                return None
            data   = await r.json()
            result = data.get("result", {})
            city = (
                result.get("admin_district")
                or result.get("region")
                or result.get("parliamentary_constituency")
                or "unknown"
            )
            city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
            pc_slug   = clean.lower()
            url = f"https://www.postcodearea.co.uk/postaltowns/{city_slug}/{pc_slug}/"
            log.info(f"Resolved {postcode} -> {url}")
            return url
    except Exception as exc:
        log.error(f"URL resolution failed for {postcode}: {exc!r}")
        return None


# ══════════════════════════════════════════════════════════════════════════
#  PAGE ACTION — cookie banner dismissal + human-ish scroll, run inside the
#  real Patchright/Playwright page Scrapling drives under the hood. This
#  replaces the manual dismiss_cookie_banner()/scroll JS from the old script.
# ══════════════════════════════════════════════════════════════════════════
async def human_page_action(page):
    for sel in [
        "button:has-text('Accept')", "button:has-text('Accept All')",
        "button:has-text('I Agree')", "button:has-text('OK')",
        "[id*='cookie'] button", "[class*='cookie'] button", "[class*='consent'] button",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                log.info("  Cookie banner dismissed")
                await asyncio.sleep(1)
                break
        except Exception:
            pass

    await page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let pos = 0;
                const step = () => {
                    pos += Math.random() * 120 + 60;
                    window.scrollTo(0, pos);
                    if (pos < document.body.scrollHeight * 0.8) {
                        setTimeout(step, Math.random() * 150 + 80);
                    } else { resolve(); }
                };
                step();
            });
        }
    """)
    await asyncio.sleep(random.uniform(READ_PAUSE_MIN, READ_PAUSE_MAX))
    return page


# ══════════════════════════════════════════════════════════════════════════
#  PAGE SCRAPER — uses AsyncStealthySession so one browser/context persists
#  across all postcodes (equivalent to reusing `page` in the old script).
#  Stealth (fingerprinting, WebRTC/canvas leaks, headless detection patches)
#  and Cloudflare-style challenge handling are built into StealthyFetcher —
#  no separate stealth library needed.
# ══════════════════════════════════════════════════════════════════════════
async def scrape_postcode(
    session: AsyncStealthySession,
    postcode: str,
    url: str,
    attempt: int = 1,
) -> PostcodeDemographics:
    log.info(f"[{attempt}/{MAX_RETRIES}] Scraping {postcode} -> {url}")
    try:
        page = await session.fetch(
            url,
            wait_selector=CONTENT_SELECTOR,
            wait_selector_state="attached",
            network_idle=True,
            page_action=human_page_action,
            timeout=PAGE_TIMEOUT_S * 1000,
        )

        if page.status in (403, 429, 503):
            log.warning(f"  HTTP {page.status} for {postcode}")
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 3)
                log.info(f"  Backing off {wait:.1f}s ...")
                await asyncio.sleep(wait)
                return await scrape_postcode(session, postcode, url, attempt + 1)
            return PostcodeDemographics(
                postcode=postcode, status="blocked",
                error=f"HTTP {page.status} after {MAX_RETRIES} attempts", scraped_url=url,
            )

        page_text = page.get_all_text(strip=True).lower()

        if len(page.body or b"") < 5000:
            log.warning(f"  Response too short for {postcode}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                return await scrape_postcode(session, postcode, url, attempt + 1)

        if "you have used" in page_text and "free daily" in page_text and "headlinenumber" not in page.body.decode(errors="ignore").lower():
            log.warning(f"  Daily view limit hit for {postcode}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                return await scrape_postcode(session, postcode, url, attempt + 1)
            return PostcodeDemographics(
                postcode=postcode, status="paywalled",
                error="Daily view limit reached", scraped_url=url,
            )

        record = parse_demographics(page, postcode, url)
        log.info(
            f"  ✓ {postcode} | pop={record.population_total} | "
            f"density={record.population_density} | income={record.household_income} | "
            f"ab_social={record.ab_social_score} | education={record.education_score} | "
            f"credit={record.credit_status_score}"
        )
        return record

    except Exception as exc:
        log.error(f"  Error on {postcode}: {exc!r}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
            return await scrape_postcode(session, postcode, url, attempt + 1)
        return PostcodeDemographics(postcode=postcode, status="failed", error=str(exc), scraped_url=url)


# ══════════════════════════════════════════════════════════════════════════
#  CSV WRITER
# ══════════════════════════════════════════════════════════════════════════
def write_csv(records: list[PostcodeDemographics], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
    log.info(f"CSV written -> {path}  ({len(records)} rows)")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
async def main() -> None:
    log.info("=" * 65)
    log.info(" postcodearea.co.uk Demographics Scraper (Scrapling edition)")
    log.info(f" Postcodes : {len(POSTCODES)}")
    log.info(f" Headless  : {HEADLESS}")
    log.info("=" * 65)

    log.info("Resolving URLs via postcodes.io ...")
    url_map: dict[str, Optional[str]] = {}
    async with aiohttp.ClientSession(headers={"User-Agent": "postcode-resolver/1.0"}) as http_session:
        for pc in POSTCODES:
            url_map[pc] = await resolve_url(http_session, pc)
            await asyncio.sleep(0.2)

    resolved   = {pc: u for pc, u in url_map.items() if u}
    unresolved = [pc for pc, u in url_map.items() if not u]
    log.info(f"Resolved {len(resolved)}/{len(POSTCODES)} URLs")
    if unresolved:
        log.warning(f"Unresolved: {unresolved}")

    records: list[PostcodeDemographics] = [
        PostcodeDemographics(postcode=pc, status="failed", error="Could not resolve demographics URL")
        for pc in unresolved
    ]

    async with AsyncStealthySession(
        headless=HEADLESS,
        proxy=PROXY_URL,
        real_chrome=True,
        block_webrtc=True,
        hide_canvas=True,
        os_randomize=True,
        geoip=True,
        humanize=True,
        locale="en-GB",
        extra_headers={"DNT": "1"},
        max_pages=1,          # keep one persistent tab, mirrors the old single `page`
    ) as session:
        # Warm-up visit — lets fingerprint/session settle before real requests
        try:
            warm = await session.fetch("https://www.postcodearea.co.uk/", network_idle=True)
            log.info(f"Warm-up: HTTP {warm.status}")
            await asyncio.sleep(random.uniform(2, 4))
        except Exception as e:
            log.warning(f"Warm-up failed: {e!r}")

        for idx, (postcode, url) in enumerate(resolved.items(), start=1):
            log.info(f"─── [{idx}/{len(resolved)}] {postcode} ───")
            record = await scrape_postcode(session, postcode, url)
            records.append(record)
            write_csv(records, OUTPUT_CSV)   # save after every postcode

            if idx < len(resolved):
                delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                log.info(f"  Waiting {delay:.1f}s ...")
                await asyncio.sleep(delay)

    ok      = sum(1 for r in records if r.status == "ok")
    failed  = sum(1 for r in records if r.status == "failed")
    blocked = sum(1 for r in records if r.status in ("blocked", "paywalled"))

    log.info("=" * 65)
    log.info(f" COMPLETE: {ok} ok | {failed} failed | {blocked} blocked")
    log.info(f" Output  : {OUTPUT_CSV}")
    log.info(f" Log     : {LOG_FILE}")
    log.info("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())