from __future__ import annotations
import asyncio
import csv
import logging
import os
import random
import sys
from dataclasses import asdict, dataclass, fields as dc_fields
from typing import Optional

from scrapling.engines.toolbelt.custom import Response
from scrapling.fetchers import AsyncStealthySession
# Configuration
@dataclass(frozen=True) #Makes code immutable after creation
class Config: 
    proxy_server: str = os.environ.get("DECODO_SERVER", "http://gb.decodo.com:30000")
    proxy_user: str = os.environ.get("DECODO_USER", "sp1tfuq8ld")
    proxy_password: str = os.environ.get("DECODO_PASS", "i~kBmigi03GkkmT4O7")

    headless: bool = True #Runs the browser without opening it
    page_timeout_ms: int = 40_000  #It will wait for 40 seconds

    page_delay_range: tuple[float, float] = (4.0, 9.0)   # pause between requests
    read_pause_range: tuple[float, float] = (2.0, 5.0)   # simulated "reading" time per page

    max_retries: int = 3
    backoff_base: float = 2.0

    output_csv: str = "demographics.csv" #Output file name 
    postcodes: tuple[str, ...] = ( #These are postcodes which will be used to scrape the data from the website
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
#Anti Detection settings for the browser session. These settings are used to make the scraping process more stealthy and avoid detection by the target website
    def browser_session_kwargs(self) -> dict:
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

# Logging
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

# Data model All the Attributes that are needed to scrape the data from the websites
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

#IT will return the field names of the PostcodeDemographics class as a list of strings. This is useful for creating CSV headers or for other purposes where you need to know the names of the fields in the data model.

CSV_FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]

# Text cleaning It will remove the white spaces if there are any 
def clean_text(value: Optional[str]) -> Optional[str]:
    return value.strip() if value else None
# Numeric cleaning It will remove the commas and white spaces if there are any

def clean_numeric(value: Optional[str]) -> Optional[str]:
    return value.replace(",", "").strip() if value else None

#It will clean the currency signs
def clean_currency(value: Optional[str]) -> Optional[str]:
    """Strip currency symbols, thousands-separator commas, and whitespace."""
    return value.replace("£", "").replace(",", "").strip() if value else None


# Demographics parser

#This code is for locatiing the card by finding image whose alt and scr contains some text and then it will read the headlineNumber value of that card.
def _find_card_by_image(
    page: Response,
    fragment: str,
    attr: str,
    exclude: Optional[str] = None,
) -> Optional[str]:
    
#Locate every <img> tag on page and lower the all attributes to make it case insensitive and then check if the fragment is present in the attribute value. If it is present then it will check if the exclude is present in the alt or src attribute of the image. If it is not present then it will find the ancestor card of that image and then read the headlineNumber value of that card.
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

#This is other card which is present at h3 class of h2 heading and will get text content from there and this is also case insensitive. It will find the ancestor card of that heading and then read the headlineNumber value of that card.

def _find_graphic_card(page: Response, heading_text: str) -> Optional[str]:
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

#This is other card which is present at h3 class of h3 heading and will get text content from there and this is also case insensitive. It will find the ancestor card of that heading and then read the sc-value value of that card.
def _find_score_card(page: Response, heading_text: str) -> Optional[str]:
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

#This is going to create a fresh record of PostcodeDemographics and then it will call the above three functions to get the values of population_density, population_total, households, household_income, ab_social_score, education_score, credit_status_score and then it will return the record.

def parse_demographics(page: Response, postcode: str, url: str) -> PostcodeDemographics:
    record = PostcodeDemographics(postcode=postcode, status="ok", scraped_url=url)

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

# Postcode -> URL resolution
#This is the manual mapping of postcode outcodes to city slugs used in the website URLs.
OUTCODE_CITY_SLUGS: dict[str, str] = {
    "SW1A": "london",
    "M1": "manchester",
    "B1": "birmingham",
    "LS1": "leeds",
    "E1": "tower-hamlets",
    "BS1": "bristol-city-of",
    "NE1": "newcastle-upon-tyne",
    "S1": "sheffield",
    "L1": "liverpool",
    "NG1": "nottingham",
    "OX1": "oxford",
    "CB2": "cambridge",
    "CV1": "coventry",
    "LE1": "leicester",
    "SO14": "southampton",
    "RG1": "reading",
    "MK9": "milton-keynes",
    "YO1": "york",
    "EX1": "exeter",
    "PL1": "plymouth",
}
#
def resolve_url(postcode: str) -> Optional[str]:
    clean = postcode.replace(" ", "").upper()
    outcode = postcode.strip().split(" ")[0].upper()

    city_slug = OUTCODE_CITY_SLUGS.get(outcode)
    if not city_slug:
        log.warning(f"No city slug mapped for outcode {outcode!r} ({postcode}) — add it to OUTCODE_CITY_SLUGS")
        return None

    url = f"https://www.postcodearea.co.uk/postaltowns/{city_slug}/{clean.lower()}/"
    log.info(f"Resolved {postcode} -> {url}")
    return url


def resolve_all_urls(postcodes: tuple[str, ...]) -> dict[str, Optional[str]]:
    return {postcode: resolve_url(postcode) for postcode in postcodes}

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

#THis will look at the cookie banner if it is present then it will click to accept that once so that it should not block the page...
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

#THis will help to wait until the content is completely avaialble to scrape 
async def wait_for_content(page) -> None:
    for selector in CONTENT_READY_SELECTORS:
        try:
            await page.wait_for_selector(selector, state="visible", timeout=12_000)
            log.info(f"  Content confirmed via: {selector}")
            return
        except Exception:
            continue

#This will scrol the pagelike a real man so that it should not be detected as bot 
async def human_scroll(page) -> None:
    await page.evaluate(HUMAN_SCROLL_SCRIPT)

#Runs the above all functions and then pause so that it should feel real like someone aftaully is looking at the content 
async def page_action(page):
    """Runs inside the page context after navigation resolves."""
    await dismiss_cookie_banner(page)
    await wait_for_content(page)
    await human_scroll(page)

    read_time = random.uniform(*CONFIG.read_pause_range)
    log.info(f"  Reading for {read_time:.1f}s ...")
    await asyncio.sleep(read_time)
    return page

# Page scraping It will look if page is at the daily limit 
def _looks_paywalled(html_lower: str) -> bool:
    has_data_cards = "headlinenumber" in html_lower or "sc-value" in html_lower
    return ("daily" in html_lower and "limit" in html_lower) and not has_data_cards

#This will scrape the data from website then convert it into the record and then return it. If it fails then it will retry for the max_retries times and if it still fails then it will return the failed record.
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
#This function will handle the retry logic for the scrape_postcode function. If the number of attempts is less than the maximum retries, it will wait for a backoff period and then retry the scrape_postcode function. If the maximum retries have been reached, it will log a warning and return a PostcodeDemographics record with a failed status...
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

#This will handle to write a recod into the csv file and it will aslo keep track of the number of records written into the csv file and then it will close the file once all the records are written into the csv file...
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

# This will log the banner with good header and confiugrations....
def _log_banner() -> None:
    log.info("=" * 65)
    log.info(" postcodearea.co.uk Demographics Scraper (Scrapling, hardened)")
    log.info(f" Postcodes : {len(CONFIG.postcodes)}")
    log.info(f" Proxy     : {CONFIG.proxy_server or '(none)'}")
    log.info(f" Headless  : {CONFIG.headless}")
    log.info(f" Timeout   : {CONFIG.page_timeout_ms} ms")
    log.info("=" * 65)

#This will return a complete summary of the scraping process including failed blocked... 
def _log_summary(records: list[PostcodeDemographics]) -> None:
    ok = sum(1 for r in records if r.status == "ok")
    failed = sum(1 for r in records if r.status == "failed")
    blocked = sum(1 for r in records if r.status in ("blocked", "paywalled"))

    log.info("=" * 65)
    log.info(f" COMPLETE: {ok} ok | {failed} failed | {blocked} blocked/paywalled")
    log.info(f" Output  : {CONFIG.output_csv}")
    log.info("=" * 65)

#This will scrape all postcodes one after other and then write record into the csv file and als handles delays in between to aviod detection...
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

#This is the main function which will call all the above functions and the it will also all the things resolved unresloved each and everything...
async def main() -> None:
    enable_utf8_console()
    _log_banner()

    log.info("Resolving postcode URLs locally ...")
    url_map = resolve_all_urls(CONFIG.postcodes)
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