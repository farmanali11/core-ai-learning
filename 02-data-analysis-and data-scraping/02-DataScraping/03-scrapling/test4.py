import asyncio
import csv
import logging
import random
import re
import sys
from dataclasses import dataclass, asdict, fields as dc_fields
from enum import Enum
from typing import Optional
from urllib.parse import urljoin

from scrapling.fetchers import StealthyFetcher

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
PROXY_URL      = f"http://{PROXY_USER}:{PROXY_PASSWORD}@gb.decodo.com:30000"

BASE_URL        = "https://www.postcodearea.co.uk"
HEADLESS        = True
PAGE_DELAY_MIN  = 4.0
PAGE_DELAY_MAX  = 9.0
READ_PAUSE_MIN  = 2.0
READ_PAUSE_MAX  = 5.0
PAGE_TIMEOUT_MS = 40_000
MAX_RETRIES     = 3
BACKOFF_BASE    = 2.0
OUTPUT_CSV      = "postcode_demographics.csv"
LOG_FILE        = "scraper.log"

POSTCODES: list[str] = [
    "SW1A 1AA", "M1 1AE", "B1 1BB", "LS1 1BA", "E1 6RF",
    "BS1 10AA", "NE1 4ST", "S1 2BJ", "L1 8JQ", "NG1 1GF",
    "OX1 1PT", "CB2 1TN", "CV1 1GF", "LE1 1SH", "PL1 1AA",
    "SO14 0YG", "RG1 1EH", "MK9 1EN", "YO1 9SB", "EX1 1GE",
]

# ══════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
#  STATUS ENUM
# ══════════════════════════════════════════════════════════════════════════
class Status(str, Enum):
    PENDING   = "pending"
    OK        = "ok"
    FAILED    = "failed"
    BLOCKED   = "blocked"
    PAYWALLED = "paywalled"


# ══════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class PostcodeDemographics:
    postcode:            str
    status:               str           = Status.PENDING.value
    error:                Optional[str] = None
    scraped_url:          Optional[str] = None

    population_total:     Optional[str] = None
    population_density:   Optional[str] = None
    households:            Optional[str] = None
    household_income:      Optional[str] = None

    ab_social_score:        Optional[str] = None
    education_score:        Optional[str] = None
    credit_status_score:    Optional[str] = None


FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]


# ══════════════════════════════════════════════════════════════════════════
#  PARSER  (Scrapling Adaptor — page.css / page.css_first)
# ══════════════════════════════════════════════════════════════════════════
def find_ancestor_card(node):
    card = node.parent
    while card is not None and not (
        card.attrib.get("class") and "card" in card.attrib.get("class", "")
    ):
        card = card.parent
    return card


def card_by_image(page, *, match_attr: str, fragment: str) -> Optional[str]:
    imgs = page.css(f"img[{match_attr}*='{fragment}' i]")
    if not imgs:
        return None
    card = find_ancestor_card(imgs[0])
    if card is None:
        return None
    el = card.css_first(".headlineNumber")
    if not el:
        return None
    return el.text.strip().replace(",", "").replace("£", "").strip()


def score_card(page, heading_text: str) -> Optional[str]:
    for h3 in page.css("h3.h3"):
        if h3.text.strip().lower() == heading_text.lower():
            card = find_ancestor_card(h3)
            if card is not None:
                val = card.css_first("span.sc-value")
                if val:
                    return val.text.strip()
    return None


def parse_demographics(page, postcode: str, url: str) -> PostcodeDemographics:
    rec = PostcodeDemographics(postcode=postcode, status=Status.OK.value, scraped_url=url)

    rec.population_total = (
        card_by_image(page, match_attr="src", fragment="icons/population.png")
        or card_by_image(page, match_attr="alt", fragment="- Population")
        or card_by_image(page, match_attr="alt", fragment="Population")
    )

    rec.population_density = (
        card_by_image(page, match_attr="src", fragment="icons/population_density.png")
        or card_by_image(page, match_attr="alt", fragment="Population Density")
    )

    try:
        for h2 in page.css("h2.h3"):
            if "households" in h2.text.strip().lower():
                card = find_ancestor_card(h2)
                if card is not None:
                    el = card.css_first("h3.headlineNumber")
                    if el:
                        rec.households = el.text.strip().replace(",", "").strip()
                break
    except Exception as exc:
        log.debug(f"  households extraction failed for {postcode}: {exc!r}")

    try:
        for h2 in page.css("h2.h3"):
            if "household income" in h2.text.strip().lower():
                card = find_ancestor_card(h2)
                if card is not None:
                    el = card.css_first("h3.headlineNumber")
                    if el:
                        rec.household_income = (
                            el.text.strip().replace("£", "").replace(",", "").strip()
                        )
                break
    except Exception as exc:
        log.debug(f"  household_income extraction failed for {postcode}: {exc!r}")

    rec.ab_social_score     = score_card(page, "AB Social Score")
    rec.education_score     = score_card(page, "Education Score")
    rec.credit_status_score = score_card(page, "Credit Status Score")

    return rec


# ══════════════════════════════════════════════════════════════════════════
#  URL RESOLUTION — no postcodes.io. We hit /search?postcode=... and pull
#  the canonical /postaltowns/{city}/{postcode}/ link straight out of the
#  search results / redirect target, exactly like the site does natively.
# ══════════════════════════════════════════════════════════════════════════
def build_search_url(postcode: str) -> str:
    clean = postcode.replace(" ", "").upper()
    return f"{BASE_URL}/search?postcode={clean}"


def extract_detail_url(page, postcode: str) -> Optional[str]:
    """
    Given the (possibly-redirected) search response page, find the
    canonical detail page URL. Handles two cases:
      1. The response already landed on /postaltowns/.../ (auto-redirect
         for an exact single match) — page.url tells us this directly.
      2. The response is still a search-results listing containing an
         <a href="/postaltowns/city/pc/"> link — parse it out.
    """
    current_url = getattr(page, "url", "") or ""
    if "/postaltowns/" in current_url:
        return current_url

    pc_slug = postcode.replace(" ", "").lower()

    links = page.css("a[href*='/postaltowns/']")
    if not links:
        return None

    # Prefer a link whose href actually contains this postcode's slug
    for a in links:
        href = a.attrib.get("href", "")
        if pc_slug in href.replace(" ", "").lower():
            return urljoin(BASE_URL, href)

    # Fallback: just take the first postaltowns link found (single-result page)
    href = links[0].attrib.get("href", "")
    return urljoin(BASE_URL, href) if href else None


# ══════════════════════════════════════════════════════════════════════════
#  CONTENT CHECK
# ══════════════════════════════════════════════════════════════════════════
def has_content(page) -> bool:
    for selector in [
        "div.headlineNumber",
        "h3.headlineNumber",
        "span.sc-value",
        "div.sc-gauge",
        "h1",
    ]:
        if page.css_first(selector):
            log.info(f"  Content confirmed via: {selector}")
            return True
    return False


def dismiss_cookie_banner_js() -> str:
    return """
    () => {
        const texts = ['Accept All', 'Accept', 'I Agree', 'OK'];
        const buttons = Array.from(document.querySelectorAll('button'));
        for (const t of texts) {
            const btn = buttons.find(b => b.textContent.trim().toLowerCase() === t.toLowerCase());
            if (btn) { btn.click(); return true; }
        }
        const cookieBtn = document.querySelector("[id*='cookie'] button, [class*='cookie'] button, [class*='consent'] button");
        if (cookieBtn) { cookieBtn.click(); return true; }
        return false;
    }
    """


async def page_action(page):
    try:
        await page.evaluate(dismiss_cookie_banner_js())
        await asyncio.sleep(1)
    except Exception as exc:
        log.debug(f"  cookie dismiss failed: {exc!r}")

    try:
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
    except Exception as exc:
        log.debug(f"  scroll failed: {exc!r}")

    await asyncio.sleep(random.uniform(READ_PAUSE_MIN, READ_PAUSE_MAX))
    return page


async def fetch_page(url: str):
    return await StealthyFetcher.async_fetch(
        url,
        headless=HEADLESS,
        proxy=PROXY_URL,
        network_idle=True,
        timeout=PAGE_TIMEOUT_MS,
        page_action=page_action,
        google_search=True,
    )


# ══════════════════════════════════════════════════════════════════════════
#  PAGE SCRAPER — two-stage (search -> resolve -> detail), iterative retry
# ══════════════════════════════════════════════════════════════════════════
async def scrape_postcode(postcode: str) -> PostcodeDemographics:
    search_url = build_search_url(postcode)
    last_error: Optional[str] = None

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"[{attempt}/{MAX_RETRIES}] Resolving {postcode} -> {search_url}")
        try:
            # ── Stage 1: hit the search endpoint, resolve the detail URL ──
            search_page = await fetch_page(search_url)
            search_status = getattr(search_page, "status", 0)

            if search_status in (403, 429, 503):
                last_error = f"HTTP {search_status} (search)"
                log.warning(f"  {last_error} for {postcode}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 3))
                    continue
                return PostcodeDemographics(
                    postcode=postcode, status=Status.BLOCKED.value,
                    error=last_error, scraped_url=search_url,
                )

            detail_url = extract_detail_url(search_page, postcode)
            if not detail_url:
                last_error = "Could not resolve detail URL from search page"
                log.warning(f"  {last_error} for {postcode}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                    continue
                return PostcodeDemographics(
                    postcode=postcode, status=Status.FAILED.value,
                    error=last_error, scraped_url=search_url,
                )

            log.info(f"  Resolved {postcode} -> {detail_url}")

            # If stage 1 already redirected onto the detail page, reuse it —
            # no need to fetch again.
            if getattr(search_page, "url", "") == detail_url:
                detail_page = search_page
            else:
                await asyncio.sleep(random.uniform(1.5, 3.0))
                detail_page = await fetch_page(detail_url)

            detail_status = getattr(detail_page, "status", 0)
            if detail_status in (403, 429, 503):
                last_error = f"HTTP {detail_status} (detail)"
                log.warning(f"  {last_error} for {postcode}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 3))
                    continue
                return PostcodeDemographics(
                    postcode=postcode, status=Status.BLOCKED.value,
                    error=last_error, scraped_url=detail_url,
                )

            if not has_content(detail_page):
                log.warning(f"  Content selectors not found for {postcode}")

            html = detail_page.html_content if hasattr(detail_page, "html_content") else str(detail_page)

            if len(html) < 5000:
                last_error = "HTML too short"
                log.warning(f"  {last_error} ({len(html)} chars) for {postcode}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                    continue
                return PostcodeDemographics(
                    postcode=postcode, status=Status.FAILED.value,
                    error=last_error, scraped_url=detail_url,
                )

            html_lower = html.lower()
            if (
                "you have used" in html_lower
                and "free daily" in html_lower
                and "headlinenumber" not in html_lower
            ):
                last_error = "Daily view limit reached"
                log.warning(f"  {last_error} for {postcode}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                    continue
                return PostcodeDemographics(
                    postcode=postcode, status=Status.PAYWALLED.value,
                    error=last_error, scraped_url=detail_url,
                )

            record = parse_demographics(detail_page, postcode, detail_url)
            log.info(
                f"  ✓ {postcode} | pop={record.population_total} | "
                f"density={record.population_density} | income={record.household_income} | "
                f"ab_social={record.ab_social_score} | education={record.education_score} | "
                f"credit={record.credit_status_score}"
            )
            return record

        except Exception as exc:
            log.error(f"  Error on {postcode} (attempt {attempt}): {exc!r}")
            last_error = str(exc)

        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))

    return PostcodeDemographics(
        postcode=postcode, status=Status.FAILED.value,
        error=last_error, scraped_url=search_url,
    )


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
    log.info(" postcodearea.co.uk Demographics Scraper (Scrapling)")
    log.info(f" Postcodes : {len(POSTCODES)}")
    log.info(f" Proxy     : {PROXY_SERVER}")
    log.info(f" Headless  : {HEADLESS}")
    log.info("=" * 65)

    records: list[PostcodeDemographics] = []

    for idx, postcode in enumerate(POSTCODES, start=1):
        log.info(f"─── [{idx}/{len(POSTCODES)}] {postcode} ───")

        record = await scrape_postcode(postcode)
        records.append(record)
        write_csv(records, OUTPUT_CSV)

        if idx < len(POSTCODES):
            delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
            log.info(f"  Waiting {delay:.1f}s ...")
            await asyncio.sleep(delay)

    ok      = sum(1 for r in records if r.status == Status.OK.value)
    failed  = sum(1 for r in records if r.status == Status.FAILED.value)
    blocked = sum(1 for r in records if r.status in (Status.BLOCKED.value, Status.PAYWALLED.value))

    log.info("=" * 65)
    log.info(f" COMPLETE: {ok} ok | {failed} failed | {blocked} blocked")
    log.info(f" Output  : {OUTPUT_CSV}")
    log.info(f" Log     : {LOG_FILE}")
    log.info("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())