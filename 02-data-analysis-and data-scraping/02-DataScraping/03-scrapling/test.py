#!/usr/bin/env python3
"""
postcodearea.co.uk — Demographics Scraper
==========================================
Stack   : asyncio + Playwright + playwright-stealth + BeautifulSoup4
Target  : https://www.postcodearea.co.uk/postaltowns/{city}/{postcode}/
Proxy   : Decodo rotating proxy (gb.decodo.com:30000)
"""

import asyncio
import csv
import logging
import random
import re
import sys
from dataclasses import dataclass, asdict, fields as dc_fields
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import (
    async_playwright, Page, TimeoutError as PWTimeout
)
from playwright_stealth import Stealth

# ── UTF-8 on Windows ────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
PROXY_SERVER   = "http://gb.decodo.com:30000"
PROXY_USER     = "sp1tfuq8ld"
PROXY_PASSWORD = "i~kBmigi03GkkmT4O7"

HEADLESS       = True
VIEWPORT       = {"width": 1366, "height": 768}
USER_AGENT     = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

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
    "SW1A 1AA",  # Westminster, London
    "M1 1AE",    # Manchester city centre
    "B1 1BB",    # Birmingham city centre
    "LS1 1BA",   # Leeds city centre
    "E1 6RF",    # Tower Hamlets, London
    "BS1 1TR",   # Bristol city centre
    "NE1 4ST",   # Newcastle city centre
    "S1 2BJ",    # Sheffield city centre
    "L1 8JQ",    # Liverpool city centre
    "NG1 1GF",   # Nottingham city centre
    "OX1 1PT",   # Oxford city centre
    "CB2 1TN",   # Cambridge city centre
    "CV1 1GF",   # Coventry city centre
    "LE1 1SH",   # Leicester city centre
    "PL1 1RH",   # Plymouth city centre
    "SO14 0YG",  # Southampton city centre
    "RG1 1EH",   # Reading city centre
    "MK9 1EN",   # Milton Keynes
    "YO1 9SB",   # York city centre
    "EX1 1GE",   # Exeter city centre
]

# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL  — fields confirmed from real B1 Birmingham HTML
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class PostcodeDemographics:
    # ── Meta ──────────────────────────────────────────────
    postcode:             str
    status:               str           = "pending"
    error:                Optional[str] = None
    scraped_url:          Optional[str] = None

    # ── 1. Population ─────────────────────────────────────
    population_total:     Optional[str] = None   # card: icons/population.png
    population_density:   Optional[str] = None   # card: icons/population_density.png
    population_growth:    Optional[str] = None   # card: icons/growth.png
    average_age:          Optional[str] = None   # span.stat in paragraph
    age_children_pct:     Optional[str] = None   # card: icons/children.png
    age_retired_pct:      Optional[str] = None   # card: icons/retired.png
    gender_male:          Optional[str] = None   # headlineNumber "48% male"
    gender_female:        Optional[str] = None   # headlineNumber "52% female"

    # ── 2. Households & Income ────────────────────────────
    households:           Optional[str] = None   # graphic card h3.headlineNumber
    household_income:     Optional[str] = None   # graphic card h3.headlineNumber
    poverty_rate:         Optional[str] = None   # "Poverty rate: 15%"
    avg_house_price:      Optional[str] = None   # span.stat in paragraph
    avg_salary:           Optional[str] = None   # span.stat in paragraph

    # ── 3. Employment ─────────────────────────────────────
    employment_rate:      Optional[str] = None   # card: icons/certificate.png
    unemployed_pct:       Optional[str] = None   # card + narrative fallback
    student_pct:          Optional[str] = None   # span.stat in paragraph

    # ── 4. Ethnicity ──────────────────────────────────────
    ethnicity_white_pct:  Optional[str] = None   # span.stat paragraph
    ethnicity_asian_pct:  Optional[str] = None   # span.stat paragraph
    ethnicity_black_pct:  Optional[str] = None   # span.stat paragraph

    # ── 5. Health ─────────────────────────────────────────
    health_very_good_pct: Optional[str] = None   # myBar row
    health_good_pct:      Optional[str] = None   # myBar row
    health_fair_pct:      Optional[str] = None   # myBar row
    health_bad_pct:       Optional[str] = None   # myBar row
    health_very_bad_pct:  Optional[str] = None   # myBar row

    # ── 6. Marital Status ─────────────────────────────────
    married_pct:          Optional[str] = None   # myBar "Married" exact
    single_pct:           Optional[str] = None   # myBar "Unmarried"
    divorced_pct:         Optional[str] = None   # myBar "Divorced"
    widowed_pct:          Optional[str] = None   # myBar "Widowed"

    # ── 7. Deprivation ────────────────────────────────────
    deprivation_zero_pct: Optional[str] = None   # myBar "Zero deprivation"


FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]


# ══════════════════════════════════════════════════════════════════════════════
#  PARSER  — confirmed against real B1 Birmingham page HTML
# ══════════════════════════════════════════════════════════════════════════════
def parse_demographics(html: str, postcode: str, url: str) -> PostcodeDemographics:
    """
    Three-layer parser based on real page HTML structure.

    Layer 1: img alt-text → parent .card → .headlineNumber  (stat cards)
    Layer 2: span.stat inside <p> paragraphs                (inline stats)
    Layer 3: div.myBar rows → .amount-pc                    (bar charts)
    """
    rec  = PostcodeDemographics(postcode=postcode, status="ok", scraped_url=url)
    soup = BeautifulSoup(html, "html.parser")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def card_by_alt(alt_fragment: str) -> Optional[str]:
        """img with alt containing fragment → nearest .card → .headlineNumber"""
        img = soup.find(
            "img",
            alt=lambda a: a and alt_fragment.lower() in a.lower()
        )
        if not img:
            return None
        card = img.find_parent("div", class_="card") or img.find_parent("div")
        if not card:
            return None
        el = card.find(class_="headlineNumber")
        if el:
            return (
                el.get_text(strip=True)
                .replace(",", "")
                .replace("£", "")
                .strip()
            )
        return None

    def card_by_src(src_fragment: str) -> Optional[str]:
        """img with src containing fragment → nearest .card → .headlineNumber"""
        img = soup.find(
            "img",
            src=lambda s: s and src_fragment in s
        )
        if not img:
            return None
        card = img.find_parent("div", class_="card") or img.find_parent("div")
        if not card:
            return None
        el = card.find(class_="headlineNumber")
        if el:
            return (
                el.get_text(strip=True)
                .replace(",", "")
                .replace("£", "")
                .strip()
            )
        return None

    def mybar_stat(label_exact: str) -> Optional[str]:
        """div.myBar where span.description text == label → div.amount-pc"""
        for bar in soup.find_all("div", class_="myBar"):
            desc = bar.find("span", class_="description")
            if desc and desc.get_text(strip=True).lower() == label_exact.lower():
                val = bar.find("div", class_="amount-pc")
                if val:
                    return val.get_text(strip=True)
        return None

    def mybar_contains(label_fragment: str) -> Optional[str]:
        """div.myBar where span.description contains fragment → div.amount-pc"""
        for bar in soup.find_all("div", class_="myBar"):
            desc = bar.find("span", class_="description")
            if desc and label_fragment.lower() in desc.get_text(strip=True).lower():
                val = bar.find("div", class_="amount-pc")
                if val:
                    return val.get_text(strip=True)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYER 1 — Stat cards (src-based first, then alt-based fallback)
    # ══════════════════════════════════════════════════════════════════════════

    # Population total
    # src: icons/population.png  |  alt: "- Population"
    rec.population_total = (
        card_by_src("icons/population.png")
        or card_by_alt("- Population")
        or card_by_alt("Population")
    )

    # Population density
    rec.population_density = (
        card_by_src("icons/population_density.png")
        or card_by_alt("Population Density")
    )

    # Population growth
    # icon confirmed as icons/growth.png in B1 HTML
    rec.population_growth = (
        card_by_src("icons/growth.png")
        or card_by_src("icons/population_growth.png")
        or card_by_alt("Population Growth")
    )

    # Children %  — icons/children.png
    rec.age_children_pct = (
        card_by_src("icons/children.png")
        or card_by_alt("Percentage of Children")
        or card_by_alt("- Children")
    )

    # Retired %  — icons/retired.png
    rec.age_retired_pct = (
        card_by_src("icons/retired.png")
        or card_by_alt("- Retired")
        or card_by_alt("Retired")
    )

    # Employment rate  — icons/certificate.png
    rec.employment_rate = (
        card_by_src("icons/certificate.png")
        or card_by_alt("Employment Rate")
    )

    # Unemployment rate  — icons/unemployed.png
    rec.unemployed_pct = (
        card_by_src("icons/unemployed.png")
        or card_by_alt("Unemployment Rate")
    )

    # Households graphic card
    # Structure: h2.h3 "Households" → parent .card → h3.headlineNumber
    try:
        hh_h2 = soup.find(
            "h2", class_="h3",
            string=lambda s: s and "Households" in s
        )
        if hh_h2:
            card = hh_h2.find_parent("div", class_="card")
            if card:
                el = card.find("h3", class_="headlineNumber")
                if el:
                    rec.households = (
                        el.get_text(strip=True).replace(",", "").strip()
                    )
    except Exception:
        pass

    # Household income graphic card
    # Structure: h2.h3 "Household Income" → parent .card → h3.headlineNumber
    try:
        inc_h2 = soup.find(
            "h2", class_="h3",
            string=lambda s: s and "Household Income" in s
        )
        if inc_h2:
            card = inc_h2.find_parent("div", class_="card")
            if card:
                el = card.find("h3", class_="headlineNumber")
                if el:
                    rec.household_income = (
                        el.get_text(strip=True)
                        .replace("£", "").replace(",", "").strip()
                    )
    except Exception:
        pass

    # Gender ratio
    # headlineNumber containing "48% male\n52% female"
    try:
        for el in soup.find_all(class_="headlineNumber"):
            txt = el.get_text(strip=True).lower()
            if "male" in txt and "female" in txt:
                m = re.search(r"(\d+)%\s*male",   txt)
                f = re.search(r"(\d+)%\s*female", txt)
                if m:
                    rec.gender_male   = m.group(1) + "%"
                if f:
                    rec.gender_female = f.group(1) + "%"
                break
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYER 2 — span.stat inside <p> paragraphs
    # ══════════════════════════════════════════════════════════════════════════

    try:
        for p in soup.find_all("p"):
            txt = p.get_text(" ", strip=True).lower()

            # Average age: "average age of <span class='stat'>34.1</span>"
            if not rec.average_age and "average age" in txt:
                span = p.find("span", class_="stat")
                if span:
                    rec.average_age = span.get_text(strip=True)

            # Average house price
            if not rec.avg_house_price and "average house price" in txt:
                span = p.find("span", class_="stat")
                if span:
                    rec.avg_house_price = span.get_text(strip=True)

            # Average salary
            if not rec.avg_salary and "average salary" in txt:
                spans = p.find_all("span", class_="stat")
                if spans:
                    rec.avg_salary = spans[0].get_text(strip=True)

            # Student %: "accounting for <span>15.7%</span> of the population"
            if not rec.student_pct and "student" in txt:
                for span in p.find_all("span", class_="stat"):
                    val = span.get_text(strip=True)
                    if "%" in val:
                        rec.student_pct = val
                        break

            # Ethnicity — paragraph containing all three groups
            # "40.6% Asian residents, followed by 34.7% White and 13.4% Black"
            if (
                not rec.ethnicity_white_pct
                and "asian" in txt
                and "white" in txt
                and "black" in txt
            ):
                p_html = str(p)
                for colour, attr in [
                    ("White", "ethnicity_white_pct"),
                    ("Asian", "ethnicity_asian_pct"),
                    ("Black", "ethnicity_black_pct"),
                ]:
                    m = re.search(
                        r'<span[^>]*class="stat"[^>]*>([\d.]+%?)</span>\s*' + colour,
                        p_html, re.I
                    )
                    if m:
                        val = m.group(1)
                        if "%" not in val:
                            val += "%"
                        setattr(rec, attr, val)

    except Exception:
        pass

    # Poverty rate (plain text, not inside span)
    try:
        full_text = soup.get_text(separator=" ")
        m = re.search(r"Poverty rate:\s*([0-9]+%)", full_text, re.I)
        if m:
            rec.poverty_rate = m.group(1)
    except Exception:
        pass

    # Unemployment narrative fallback
    if not rec.unemployed_pct:
        try:
            full_text = soup.get_text(separator=" ")
            m = re.search(r"unemployment rate of ([0-9.]+)%?", full_text, re.I)
            if m:
                rec.unemployed_pct = m.group(1) + "%"
        except Exception:
            pass

    # Ethnicity white from diversity card narrative fallback
    if not rec.ethnicity_white_pct:
        try:
            for p in soup.find_all("p"):
                if "identifying as white" in p.get_text().lower():
                    m = re.search(
                        r"(\d+)%\s*of residents identifying as White",
                        p.get_text(), re.I
                    )
                    if m:
                        rec.ethnicity_white_pct = m.group(1) + "%"
                    break
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  LAYER 3 — myBar chart rows  (exact label match preferred)
    # ══════════════════════════════════════════════════════════════════════════

    # Health — confirmed labels from B1 HTML
    rec.health_very_good_pct = mybar_stat("Very good health")
    rec.health_good_pct      = mybar_stat("Good health")
    rec.health_fair_pct      = mybar_stat("Fair health")
    rec.health_bad_pct       = mybar_stat("Bad health")
    rec.health_very_bad_pct  = mybar_stat("Very bad health")

    # Marital status — use exact labels to avoid partial matches
    # "Married" not "Living in a couple (married)"
    rec.married_pct  = mybar_stat("Married")
    rec.single_pct   = mybar_stat("Unmarried")
    rec.divorced_pct = mybar_stat("Divorced")
    rec.widowed_pct  = mybar_stat("Widowed")

    # Deprivation
    rec.deprivation_zero_pct = mybar_stat("Zero deprivation")

    return rec


# ══════════════════════════════════════════════════════════════════════════════
#  URL RESOLVER  — postcodes.io → postcodearea.co.uk URL
# ══════════════════════════════════════════════════════════════════════════════
async def resolve_url(
    session: aiohttp.ClientSession, postcode: str
) -> Optional[str]:
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
            city   = (
                result.get("admin_district")
                or result.get("region")
                or result.get("parliamentary_constituency")
                or "unknown"
            )
            city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
            pc_slug   = clean.lower()
            url = (
                f"https://www.postcodearea.co.uk"
                f"/postaltowns/{city_slug}/{pc_slug}/"
            )
            log.info(f"Resolved {postcode} -> {url}")
            return url
    except Exception as exc:
        log.error(f"URL resolution failed for {postcode}: {exc!r}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  STEALTH CONTEXT
# ══════════════════════════════════════════════════════════════════════════════
def build_stealth() -> Stealth:
    return Stealth(
        navigator_webdriver          = True,
        navigator_platform_override  = "Win32",
        navigator_languages_override = ("en-GB", "en"),
        navigator_vendor_override    = "Google Inc.",
        webgl_vendor_override        = "Intel Inc.",
        webgl_renderer_override      = "Intel Iris OpenGL Engine",
        chrome_app                   = True,
        chrome_csi                   = True,
        chrome_load_times            = True,
        media_codecs                 = True,
        navigator_plugins            = True,
    )


async def make_context(playwright, use_proxy: bool = True) -> tuple:
    proxy_cfg = (
        {
            "server":   PROXY_SERVER,
            "username": PROXY_USER,
            "password": PROXY_PASSWORD,
        }
        if use_proxy else None
    )
    browser = await playwright.chromium.launch(
        headless = HEADLESS,
        proxy    = proxy_cfg,
        args     = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    context = await browser.new_context(
        user_agent = USER_AGENT,
        viewport   = VIEWPORT,
        locale     = "en-GB",
        timezone_id= "Europe/London",
        proxy      = proxy_cfg,
        extra_http_headers={
            "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language":           "en-GB,en;q=0.9",
            "Accept-Encoding":           "gzip, deflate, br",
            "Connection":                "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest":            "document",
            "Sec-Fetch-Mode":            "navigate",
            "Sec-Fetch-Site":            "none",
            "Sec-Fetch-User":            "?1",
            "DNT":                       "1",
        },
    )
    stealth = build_stealth()
    await stealth.apply_stealth_async(context)
    return browser, context


# ══════════════════════════════════════════════════════════════════════════════
#  COOKIE BANNER
# ══════════════════════════════════════════════════════════════════════════════
async def dismiss_cookie_banner(page: Page) -> None:
    for sel in [
        "button:has-text('Accept')",
        "button:has-text('Accept All')",
        "button:has-text('I Agree')",
        "button:has-text('OK')",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
        "[class*='consent'] button",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                log.info("  Cookie banner dismissed")
                await asyncio.sleep(1)
                return
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  WAIT FOR CONTENT — ensures JS-rendered cards are in DOM
# ══════════════════════════════════════════════════════════════════════════════
async def wait_for_content(page: Page) -> bool:
    """Wait for at least one .headlineNumber to appear — confirms content loaded."""
    for selector in [
        "div.headlineNumber",
        "h3.headlineNumber",
        "div.myBar",
        "span.stat",
        "h1",
    ]:
        try:
            await page.wait_for_selector(
                selector, state="visible", timeout=12_000
            )
            log.info(f"  Content confirmed via: {selector}")
            return True
        except Exception:
            continue
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
async def scrape_postcode(
    page:     Page,
    postcode: str,
    url:      str,
    attempt:  int = 1,
) -> PostcodeDemographics:
    log.info(f"[{attempt}/{MAX_RETRIES}] Scraping {postcode} -> {url}")

    try:
        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT_MS,
        )
        http_status = response.status if response else 0

        if http_status in (403, 429, 503):
            log.warning(f"  HTTP {http_status} for {postcode}")
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 3)
                log.info(f"  Backing off {wait:.1f}s ...")
                await asyncio.sleep(wait)
                return await scrape_postcode(page, postcode, url, attempt + 1)
            return PostcodeDemographics(
                postcode=postcode, status="blocked",
                error=f"HTTP {http_status} after {MAX_RETRIES} attempts",
                scraped_url=url,
            )

        await dismiss_cookie_banner(page)

        # Wait for actual card content to render
        content_ok = await wait_for_content(page)
        if not content_ok:
            log.warning(f"  Content selectors not found for {postcode}")

        # Slow scroll to trigger lazy sections
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

        read_time = random.uniform(READ_PAUSE_MIN, READ_PAUSE_MAX)
        log.info(f"  Page loaded ({http_status}) — reading for {read_time:.1f}s ...")
        await asyncio.sleep(read_time)

        html = await page.content()

        # Sanity check
        if len(html) < 5000:
            log.warning(f"  HTML too short ({len(html)} chars) for {postcode}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                return await scrape_postcode(page, postcode, url, attempt + 1)

        # Paywall check
        html_lower = html.lower()
        if (
            "you have used" in html_lower
            and "free daily" in html_lower
            and "headlinenumber" not in html_lower
        ):
            log.warning(f"  Daily view limit hit for {postcode}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                return await scrape_postcode(page, postcode, url, attempt + 1)
            return PostcodeDemographics(
                postcode=postcode, status="paywalled",
                error="Daily view limit reached",
                scraped_url=url,
            )

        record = parse_demographics(html, postcode, url)
        log.info(
            f"  ✓ {postcode} | "
            f"pop={record.population_total} | "
            f"age={record.average_age} | "
            f"income={record.household_income} | "
            f"white={record.ethnicity_white_pct} | "
            f"health_vg={record.health_very_good_pct}"
        )
        return record

    except PWTimeout:
        log.error(f"  Timeout on {postcode} (attempt {attempt})")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
            return await scrape_postcode(page, postcode, url, attempt + 1)
        return PostcodeDemographics(
            postcode=postcode, status="failed",
            error="Playwright timeout", scraped_url=url,
        )
    except Exception as exc:
        log.error(f"  Error on {postcode}: {exc!r}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
            return await scrape_postcode(page, postcode, url, attempt + 1)
        return PostcodeDemographics(
            postcode=postcode, status="failed",
            error=str(exc), scraped_url=url,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CSV WRITER
# ══════════════════════════════════════════════════════════════════════════════
def write_csv(records: list[PostcodeDemographics], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))
    log.info(f"CSV written -> {path}  ({len(records)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def main() -> None:
    log.info("=" * 65)
    log.info(" postcodearea.co.uk Demographics Scraper")
    log.info(f" Postcodes : {len(POSTCODES)}")
    log.info(f" Proxy     : {PROXY_SERVER}")
    log.info(f" Headless  : {HEADLESS}")
    log.info("=" * 65)

    # Step 1: resolve URLs
    log.info("Resolving URLs via postcodes.io ...")
    url_map: dict[str, Optional[str]] = {}
    async with aiohttp.ClientSession(
        headers={"User-Agent": "postcode-resolver/1.0"}
    ) as session:
        for pc in POSTCODES:
            url_map[pc] = await resolve_url(session, pc)
            await asyncio.sleep(0.2)

    resolved   = {pc: u for pc, u in url_map.items() if u}
    unresolved = [pc for pc, u in url_map.items() if not u]
    log.info(f"Resolved {len(resolved)}/{len(POSTCODES)} URLs")
    if unresolved:
        log.warning(f"Unresolved: {unresolved}")

    records: list[PostcodeDemographics] = [
        PostcodeDemographics(
            postcode=pc, status="failed",
            error="Could not resolve demographics URL"
        )
        for pc in unresolved
    ]

    # Step 2: browser scraping
    async with async_playwright() as playwright:
        use_proxy = True
        try:
            browser, context = await make_context(playwright, use_proxy=True)
            test_page = await context.new_page()
            test_resp = await test_page.goto(
                "https://www.postcodearea.co.uk/",
                wait_until="domcontentloaded",
                timeout=20_000,
            )
            log.info(f"Proxy test: HTTP {test_resp.status}")
            await dismiss_cookie_banner(test_page)
            await test_page.close()
        except Exception as e:
            log.warning(f"Proxy failed ({e!r}) — running without proxy")
            try:
                await browser.close()
            except Exception:
                pass
            use_proxy = False
            browser, context = await make_context(playwright, use_proxy=False)

        # Warm-up
        log.info("Warm-up: visiting homepage ...")
        warmup = await context.new_page()
        try:
            await warmup.goto(
                "https://www.postcodearea.co.uk/",
                wait_until="domcontentloaded",
                timeout=20_000,
            )
            await dismiss_cookie_banner(warmup)
            await asyncio.sleep(random.uniform(2, 4))
        except Exception as e:
            log.warning(f"Warm-up failed: {e!r}")
        finally:
            await warmup.close()

        page = await context.new_page()

        for idx, (postcode, url) in enumerate(resolved.items(), start=1):
            log.info(f"─── [{idx}/{len(resolved)}] {postcode} ───")
            record = await scrape_postcode(page, postcode, url)
            records.append(record)

            # Save after every postcode — never lose progress
            write_csv(records, OUTPUT_CSV)

            if idx < len(resolved):
                delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                log.info(f"  Waiting {delay:.1f}s ...")
                await asyncio.sleep(delay)

        await page.close()
        await context.close()
        await browser.close()

    # Step 3: final summary
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