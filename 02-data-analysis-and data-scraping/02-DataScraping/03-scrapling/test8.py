"""
UK postcode demographics scraper (postcodearea.co.uk), built on Scrapling.

Pipeline: resolve each postcode to a page URL via postcodes.io -> fetch each
page through a stealth browser session -> parse demographic cards from the
DOM -> write results to CSV incrementally.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import random
import re
import sys
from dataclasses import asdict, dataclass, fields as dc_fields
from typing import Optional

import aiohttp
from scrapling.engines.toolbelt.custom import Response
from scrapling.fetchers import AsyncStealthySession


# ─────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Config:
    proxy_server: str = os.environ.get("DECODO_SERVER", "http://gb.decodo.com:30000")
    proxy_user: str = os.environ.get("DECODO_USER", "sp1tfuq8ld")
    proxy_password: str = os.environ.get("DECODO_PASS", "i~kBmigi03GkkmT4O7")

    headless: bool = True
    page_timeout_ms: int = 40_000  # milliseconds (confirmed via Scrapling 0.4.9 source)

    page_delay_range: tuple[float, float] = (4.0, 9.0)   # pause between requests
    read_pause_range: tuple[float, float] = (2.0, 5.0)   # simulated "reading" time per page

    max_retries: int = 3
    backoff_base: float = 2.0

    output_csv: str = "demographics.csv"

    postcodes: tuple[str, ...] = (
        "SW1A 1AA", "M1 1AE", "B1 1BB", "LS1 1BA",
        "E1 6RF", "BS1 10AA", "NE1 4ST", "S1 2BJ",
        "L1 8JQ", "NG1 1GF", "OX1 1PT", "CB2 1TN",
        "CV1 1GF", "LE1 1SH", "PL1 1AA", "SO14 0YG",
        "RG1 1EH", "MK9 1EN", "YO1 9SB", "EX1 1GE",
    )

    @property
    def proxy(self) -> Optional[dict]:
        if not self.proxy_server:
            return None
        return {
            "server": self.proxy_server,
            "username": self.proxy_user,
            "password": self.proxy_password,
        }

    def browser_session_kwargs(self) -> dict:
        """Kwargs for AsyncStealthySession, verified field-by-field against
        the installed scrapling==0.4.9 source (engines/_browsers/_types.py)."""
        kwargs = dict(
            headless=self.headless,
            solve_cloudflare=True,
            timeout=self.page_timeout_ms,
            real_chrome=True,
            hide_canvas=True,
            block_webrtc=True,
            allow_webgl=True,
            block_ads=True,
            max_pages=1,
            retries=1,
            dns_over_https=True,
        )
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return kwargs


CONFIG = Config()


# ─────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────

def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Scrapling logs its own internal status lines under the "scrapling" logger
    # name, independent of ours. Raise its threshold so only real warnings
    # surface, without touching our own log.info(...) calls.
    logging.getLogger("scrapling").setLevel(logging.WARNING)
    return logging.getLogger("postcode_scraper")


log = configure_logging()


def enable_utf8_console() -> None:
    """Windows terminals default to a legacy codepage that can't print
    box-drawing characters or checkmarks used in the log output below."""
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class PostcodeDemographics:
    postcode: str
    status: str = "pending"
    error: Optional[str] = None
    scraped_url: Optional[str] = None

    population_total: Optional[str] = None
    population_density: Optional[str] = None
    households: Optional[str] = None
    household_income: Optional[str] = None

    ab_social_score: Optional[str] = None
    education_score: Optional[str] = None
    credit_status_score: Optional[str] = None


CSV_FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]


# ─────────────────────────────────────────────────────────────────────────
# Text cleaning
# ─────────────────────────────────────────────────────────────────────────

def clean_text(value: Optional[str]) -> Optional[str]:
    """Strip whitespace only. Used for percentage-style score values."""
    return value.strip() if value else None


def clean_numeric(value: Optional[str]) -> Optional[str]:
    """Strip thousands-separator commas and whitespace."""
    return value.replace(",", "").strip() if value else None


def clean_currency(value: Optional[str]) -> Optional[str]:
    """Strip currency symbols, thousands-separator commas, and whitespace."""
    return value.replace("£", "").replace(",", "").strip() if value else None


# ─────────────────────────────────────────────────────────────────────────
# Demographics parser
#
# Scrapling's `.css("selector::text")` returns Selectors wrapping text NODES,
# not plain strings — `.get()` is the correct call to serialize the first
# match to an actual string. `.first` would return a Selector object instead.
#
# The card-detection selectors below (h2.h3 for graphic cards, h3.h3 for
# gauge scores, the img-then-ancestor-div walk for stat cards, and the
# £/comma stripping per field) are matched against a confirmed-working
# reference implementation of this same page's structure.
# ─────────────────────────────────────────────────────────────────────────

def _find_card_by_image(
    page: Response,
    fragment: str,
    attr: str,
    exclude: Optional[str] = None,
) -> Optional[str]:
    """Locate a stat card via an <img src|alt> fragment, then read its
    .headlineNumber value. Prefers a strict .card ancestor, falling back to
    the nearest parent <div> if no .card class is present on this page."""
    fragment_lower = fragment.lower()
    for img in page.css("img"):
        attr_value = (img.attrib.get(attr) or "").lower()
        if fragment_lower not in attr_value:
            continue

        if exclude:
            alt_text = (img.attrib.get("alt") or "").lower()
            src_text = (img.attrib.get("src") or "").lower()
            if exclude.lower() in alt_text or exclude.lower() in src_text:
                continue

        card = (
            img.find_ancestor(lambda e: e.has_class("card"))
            or img.find_ancestor(lambda e: e.tag == "div")
        )
        if not card:
            continue

        text = card.css(".headlineNumber::text").get()
        if text:
            return text

    return None


def _find_graphic_card(page: Response, heading_text: str) -> Optional[str]:
    """Locate a Households / Household Income card via its <h2 class="h3">
    heading (substring match), then read the sibling .headlineNumber value."""
    heading_lower = heading_text.lower()
    for heading in page.css("h2.h3"):
        text = heading.get_all_text(strip=True)
        if text and heading_lower in text.lower():
            card = heading.find_ancestor(lambda e: e.has_class("card"))
            if card:
                value = card.css("h3.headlineNumber::text").get()
                if value:
                    return value
    return None


def _find_score_card(page: Response, heading_text: str) -> Optional[str]:
    """Locate a gauge-score card via its <h3 class="h3"> heading (exact
    match), then read the sibling span.sc-value percentage."""
    heading_lower = heading_text.lower()
    for heading in page.css("h3.h3"):
        text = heading.get_all_text(strip=True)
        if text and text.lower() == heading_lower:
            card = heading.find_ancestor(lambda e: e.has_class("card"))
            if card:
                value = card.css("span.sc-value::text").get()
                if value:
                    return value
    return None


def parse_demographics(page: Response, postcode: str, url: str) -> PostcodeDemographics:
    record = PostcodeDemographics(postcode=postcode, status="ok", scraped_url=url)

    # Density is resolved before population, and population's alt-text
    # fallback explicitly excludes "Density" -- otherwise a loose substring
    # match on "Population" can steal the Population Density card's value,
    # since "Population Density" contains "Population" as a substring.
    record.population_density = clean_currency(
        _find_card_by_image(page, "population_density.png", attr="src")
        or _find_card_by_image(page, "Population Density", attr="alt")
    )
    record.population_total = clean_currency(
        _find_card_by_image(page, "population.png", attr="src")
        or _find_card_by_image(page, "Population", attr="alt", exclude="Density")
    )
    record.households = clean_numeric(_find_graphic_card(page, "Households"))
    record.household_income = clean_currency(_find_graphic_card(page, "Household Income"))
    record.ab_social_score = clean_text(_find_score_card(page, "AB Social Score"))
    record.education_score = clean_text(_find_score_card(page, "Education Score"))
    record.credit_status_score = clean_text(_find_score_card(page, "Credit Status Score"))

    return record


# ─────────────────────────────────────────────────────────────────────────
# Postcode -> URL resolution (via postcodes.io)
# ─────────────────────────────────────────────────────────────────────────

async def resolve_url(session: aiohttp.ClientSession, postcode: str) -> Optional[str]:
    clean = postcode.replace(" ", "").upper()
    try:
        async with session.get(
            f"https://api.postcodes.io/postcodes/{clean}",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status != 200:
                log.warning(f"postcodes.io {response.status} for {postcode}")
                return None

            data = await response.json()
            result = data.get("result", {})
            city = (
                result.get("admin_district")
                or result.get("region")
                or result.get("parliamentary_constituency")
                or "unknown"
            )
            city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
            postcode_slug = clean.lower()
            url = f"https://www.postcodearea.co.uk/postaltowns/{city_slug}/{postcode_slug}/"
            log.info(f"Resolved {postcode} -> {url}")
            return url

    except Exception as exc:
        log.error(f"URL resolution failed for {postcode}: {exc!r}")
        return None


async def resolve_url_with_retry(
    session: aiohttp.ClientSession,
    postcode: str,
    retries: int = 2,
) -> Optional[str]:
    """postcodes.io is a third-party dependency; a single hiccup shouldn't
    permanently mark a postcode as unresolved for the whole run."""
    for attempt in range(retries + 1):
        url = await resolve_url(session, postcode)
        if url:
            return url
        if attempt < retries:
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def resolve_all_urls(postcodes: tuple[str, ...]) -> dict[str, Optional[str]]:
    url_map: dict[str, Optional[str]] = {}
    async with aiohttp.ClientSession(headers={"User-Agent": "postcode-resolver/1.0"}) as session:
        for postcode in postcodes:
            url_map[postcode] = await resolve_url_with_retry(session, postcode)
            await asyncio.sleep(0.2)
    return url_map


# ─────────────────────────────────────────────────────────────────────────
# In-page browser behavior (runs after navigation, inside page_action)
# ─────────────────────────────────────────────────────────────────────────

COOKIE_BANNER_SELECTORS = [
    "button:has-text('Accept')", "button:has-text('Accept All')",
    "button:has-text('I Agree')", "button:has-text('OK')",
    "[id*='cookie'] button", "[class*='cookie'] button",
    "[class*='consent'] button",
]

CONTENT_READY_SELECTORS = [
    "div.headlineNumber", "h3.headlineNumber",
    "span.sc-value", "div.sc-gauge", "h1",
]

HUMAN_SCROLL_SCRIPT = """
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
"""


async def dismiss_cookie_banner(page) -> None:
    for selector in COOKIE_BANNER_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=1500):
                await button.click()
                log.info("  Cookie banner dismissed")
                await asyncio.sleep(1)
                return
        except Exception:
            continue


async def wait_for_content(page) -> None:
    for selector in CONTENT_READY_SELECTORS:
        try:
            await page.wait_for_selector(selector, state="visible", timeout=12_000)
            log.info(f"  Content confirmed via: {selector}")
            return
        except Exception:
            continue


async def human_scroll(page) -> None:
    await page.evaluate(HUMAN_SCROLL_SCRIPT)


async def page_action(page):
    """Runs inside the page context after navigation resolves."""
    await dismiss_cookie_banner(page)
    await wait_for_content(page)
    await human_scroll(page)

    read_time = random.uniform(*CONFIG.read_pause_range)
    log.info(f"  Reading for {read_time:.1f}s ...")
    await asyncio.sleep(read_time)
    return page


# ─────────────────────────────────────────────────────────────────────────
# Page scraping
# ─────────────────────────────────────────────────────────────────────────

def _looks_paywalled(html_lower: str) -> bool:
    has_data_cards = "headlinenumber" in html_lower or "sc-value" in html_lower
    return ("daily" in html_lower and "limit" in html_lower) and not has_data_cards


async def scrape_postcode(
    session: AsyncStealthySession,
    postcode: str,
    url: str,
    is_first_request: bool,
    attempt: int = 1,
) -> PostcodeDemographics:
    log.info(f"[{attempt}/{CONFIG.max_retries}] Scraping {postcode} -> {url}")

    try:
        page: Response = await session.fetch(
            url,
            network_idle=True,
            page_action=page_action,
            # Only fake the "came from Google" referrer on the first page of
            # the session -- repeating it on every request is itself a tell.
            google_search=is_first_request,
        )

        if page.status in (403, 429, 503):
            return await _retry_or_terminal(
                session, postcode, url, is_first_request, attempt,
                status="blocked",
                error=f"HTTP {page.status} — site rejected the request",
                log_message=f"  HTTP {page.status} for {postcode} — site is blocking this request",
            )

        html = page.html_content
        if not html or len(html) < 5000:
            return await _retry_or_terminal(
                session, postcode, url, is_first_request, attempt,
                status="failed",
                error="Insufficient HTML content",
                log_message=f"  HTML too short ({len(html) if html else 0} chars) for {postcode}",
            )

        if _looks_paywalled(html.lower()):
            log.warning(f"  Free daily view limit reached for {postcode} — skipping")
            return PostcodeDemographics(
                postcode=postcode, status="paywalled",
                error="Site's free daily view limit reached", scraped_url=url,
            )

        record = parse_demographics(page, postcode, url)
        log.info(
            f"  \u2713 {postcode} | pop={record.population_total} | "
            f"density={record.population_density} | income={record.household_income} | "
            f"ab_social={record.ab_social_score} | education={record.education_score} | "
            f"credit={record.credit_status_score}"
        )
        return record

    except Exception as exc:
        return await _retry_or_terminal(
            session, postcode, url, is_first_request, attempt,
            status="failed",
            error=str(exc),
            log_message=f"  Error on {postcode}: {exc!r}",
        )


async def _retry_or_terminal(
    session: AsyncStealthySession,
    postcode: str,
    url: str,
    is_first_request: bool,
    attempt: int,
    *,
    status: str,
    error: str,
    log_message: str,
) -> PostcodeDemographics:
    """Shared retry/give-up path for scrape_postcode's failure branches."""
    log.warning(log_message)
    if attempt < CONFIG.max_retries:
        wait = CONFIG.backoff_base * (2 ** attempt) + random.uniform(0, 3)
        log.info(f"  Backing off {wait:.1f}s ...")
        await asyncio.sleep(wait)
        return await scrape_postcode(session, postcode, url, is_first_request=False, attempt=attempt + 1)

    log.warning(f"  {postcode}: giving up after {CONFIG.max_retries} attempts ({status})")
    return PostcodeDemographics(postcode=postcode, status=status, error=error, scraped_url=url)


# ─────────────────────────────────────────────────────────────────────────
# CSV output — incremental, flushed after every row so progress survives a crash
# ─────────────────────────────────────────────────────────────────────────

class CsvRecorder:
    def __init__(self, path: str):
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=CSV_FIELDNAMES)
        self._writer.writeheader()
        self.path = path
        self.count = 0

    def write(self, record: PostcodeDemographics) -> None:
        self._writer.writerow(asdict(record))
        self._file.flush()
        self.count += 1

    def close(self) -> None:
        self._file.close()
        log.info(f"CSV written -> {self.path} ({self.count} rows)")


# ─────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────

def _log_banner() -> None:
    log.info("=" * 65)
    log.info(" postcodearea.co.uk Demographics Scraper (Scrapling, hardened)")
    log.info(f" Postcodes : {len(CONFIG.postcodes)}")
    log.info(f" Proxy     : {CONFIG.proxy_server or '(none)'}")
    log.info(f" Headless  : {CONFIG.headless}")
    log.info(f" Timeout   : {CONFIG.page_timeout_ms} ms")
    log.info("=" * 65)


def _log_summary(records: list[PostcodeDemographics]) -> None:
    ok = sum(1 for r in records if r.status == "ok")
    failed = sum(1 for r in records if r.status == "failed")
    blocked = sum(1 for r in records if r.status in ("blocked", "paywalled"))

    log.info("=" * 65)
    log.info(f" COMPLETE: {ok} ok | {failed} failed | {blocked} blocked/paywalled")
    log.info(f" Output  : {CONFIG.output_csv}")
    log.info("=" * 65)


async def scrape_all(resolved: dict[str, str], recorder: CsvRecorder) -> list[PostcodeDemographics]:
    records: list[PostcodeDemographics] = []

    async with AsyncStealthySession(**CONFIG.browser_session_kwargs()) as session:
        if CONFIG.proxy:
            log.info("Using configured proxy for this session")

        for idx, (postcode, url) in enumerate(resolved.items(), start=1):
            log.info(f"\u2500\u2500\u2500 [{idx}/{len(resolved)}] {postcode} \u2500\u2500\u2500")
            record = await scrape_postcode(session, postcode, url, is_first_request=(idx == 1))
            records.append(record)
            recorder.write(record)

            # A hard block on the very first request is a diagnostic signal
            # (IP reputation / managed-challenge tier), not something later
            # retries against the rest of the list will fix.
            if idx == 1 and record.status == "blocked":
                log.error(
                    "  First request was blocked by Cloudflare. Stopping early — "
                    "this usually means IP reputation (try a different PROXY) or "
                    "headless detection (try HEADLESS = False), not a transient "
                    "issue. Fix the config and re-run rather than retrying the list."
                )
                break

            if idx < len(resolved):
                delay = random.uniform(*CONFIG.page_delay_range)
                log.info(f"  Waiting {delay:.1f}s ...")
                await asyncio.sleep(delay)

    return records


async def main() -> None:
    enable_utf8_console()
    _log_banner()

    log.info("Resolving URLs via postcodes.io ...")
    url_map = await resolve_all_urls(CONFIG.postcodes)
    resolved = {pc: url for pc, url in url_map.items() if url}
    unresolved = [pc for pc, url in url_map.items() if not url]

    log.info(f"Resolved {len(resolved)}/{len(CONFIG.postcodes)} URLs")
    if unresolved:
        log.warning(f"Unresolved: {unresolved}")

    recorder = CsvRecorder(CONFIG.output_csv)
    records: list[PostcodeDemographics] = []

    for postcode in unresolved:
        record = PostcodeDemographics(
            postcode=postcode, status="failed",
            error="Could not resolve demographics URL",
        )
        records.append(record)
        recorder.write(record)

    try:
        records.extend(await scrape_all(resolved, recorder))
    finally:
        recorder.close()

    _log_summary(records)


if __name__ == "__main__":
    asyncio.run(main())