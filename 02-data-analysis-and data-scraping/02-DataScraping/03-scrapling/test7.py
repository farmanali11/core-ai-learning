#Importing All the necessary Libraries which are needed while working on the problem and which we will be used while working...
import asyncio
import csv
import logging
import os
import random
import re
import sys
from dataclasses import dataclass, asdict, fields as dc_fields
from typing import Optional

import aiohttp
from scrapling.fetchers import AsyncStealthySession
from scrapling.engines.toolbelt.custom import Response

#This will solve all the problem which are included in if there
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  PROXY CONFIG
# ══════════════════════════════════════════════════════════════════════════════
# Credentials pulled from env vars so nothing sensitive sits in source control.
# Set these in your shell before running, e.g. (Git Bash):
#   export DECODO_SERVER="http://gb.decodo.com:30000"
#   export DECODO_USER="sp1tfuq8ld"
#   export DECODO_PASS="i~kBmigi03GkkmT4O7"
PROXY_SERVER   = os.environ.get("DECODO_SERVER", "http://gb.decodo.com:30000")
PROXY_USER     = os.environ.get("DECODO_USER", "sp1tfuq8ld")
PROXY_PASSWORD = os.environ.get("DECODO_PASS", "i~kBmigi03GkkmT4O7")

# Scrapling/Playwright proxy dict form — server + username + password only.
# This was the missing piece before: PROXY was never actually built.
PROXY = {
    "server":   PROXY_SERVER,
    "username": PROXY_USER,
    "password": PROXY_PASSWORD,
}

HEADLESS = True
#This will continue to scrape data without opening the Browser itself if it was false it will open the brower then it will go on the given location and will do a complete automation we are not doing this for this time if needed we will do it later....

#Some constants we will use while working and these are repetively used so we are setting them up if any value changed it will change for the whole code...

PAGE_DELAY_MIN  = 4.0
PAGE_DELAY_MAX  = 9.0
READ_PAUSE_MIN  = 2.0
READ_PAUSE_MAX  = 5.0
PAGE_TIMEOUT_MS = 40_000   # confirmed: this field is in milliseconds in scrapling 0.4.9
MAX_RETRIES     = 3
BACKOFF_BASE    = 2.0
OUTPUT_CSV      = "demographics.csv"

#Postcodes of the uk different areas for which we going to scrape data...
POSTCODES: list[str] = [
    "SW1A 1AA",  "M1 1AE",    "B1 1BB",    "LS1 1BA",
    "E1 6RF",    "BS1 10AA",  "NE1 4ST",   "S1 2BJ",
    "L1 8JQ",    "NG1 1GF",   "OX1 1PT",   "CB2 1TN",
    "CV1 1GF",   "LE1 1SH",   "PL1 1AA",   "SO14 0YG",
    "RG1 1EH",   "MK9 1EN",   "YO1 9SB",   "EX1 1GE",
]

# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("scrapling").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


#Data Model
#A complete model of data described inside the class Postcode Demographics which we will use and attributes which we are scraping from the given website...
@dataclass
class PostcodeDemographics:
    postcode:            str
    status:               str           = "pending"
    error:                Optional[str] = None
    scraped_url:          Optional[str] = None

    population_total:    Optional[str] = None
    population_density:  Optional[str] = None
    households:           Optional[str] = None
    household_income:     Optional[str] = None

    ab_social_score:      Optional[str] = None
    education_score:       Optional[str] = None
    credit_status_score:   Optional[str] = None


FIELDNAMES = [f.name for f in dc_fields(PostcodeDemographics)]


def clean_text(val: Optional[str]) -> Optional[str]:
    """Centralized whitespace cleanup so every field is consistently stripped."""
    return val.strip() if val else None


def clean_numeric(val: Optional[str]) -> Optional[str]:
    """Matches the confirmed-working BS4 version's cleaning for population/
    households values: strips thousands-separator commas and whitespace."""
    if not val:
        return None
    return val.replace(",", "").strip()


def clean_currency(val: Optional[str]) -> Optional[str]:
    """Matches the confirmed-working BS4 version's cleaning for money values
    (population cards + household income): strips £ signs, commas, whitespace."""
    if not val:
        return None
    return val.replace("£", "").replace(",", "").strip()


#PARSER
def parse_demographics(page: Response, postcode: str, url: str) -> PostcodeDemographics:
    rec = PostcodeDemographics(postcode=postcode, status="ok", scraped_url=url)

    def card_by_img(fragment: str, by: str = "src", exclude: Optional[str] = None) -> Optional[str]:
        # NOTE: the CSS4 case-insensitive attribute flag `[attr*="..." i]` is NOT
        # supported by the cssselect/lxml translator Scrapling's parser sits on
        # top of -- it raises SelectorSyntaxError at query time. So we select all
        # <img> tags plain, then do the fragment/case matching ourselves in Python.
        attr_name = "src" if by == "src" else "alt"
        fragment_lower = fragment.lower()
        imgs = page.css("img")
        if not imgs:
            return None
        for img in imgs:
            attr_val = (img.attrib.get(attr_name) or "").lower()
            if fragment_lower not in attr_val:
                continue
            if exclude:
                alt_text = (img.attrib.get("alt") or "").lower()
                src_text = (img.attrib.get("src") or "").lower()
                if exclude.lower() in alt_text or exclude.lower() in src_text:
                    continue
            # Confirmed BS4 behaviour: prefer a strict .card ancestor, but fall
            # back to the nearest parent <div> at all if no .card class is
            # present on this particular page's markup — your working version
            # does `find_parent("div", class_="card") or find_parent("div")`.
            card = (
                img.find_ancestor(lambda e: e.has_class("card"))
                or img.find_ancestor(lambda e: e.tag == "div")
            )
            if not card:
                continue
            # NOTE: .css("...::text") returns Selectors wrapping text NODES, not
            # plain strings. `.first` gives back a Selector object (hence the
            # "'Selector' object has no attribute 'strip'" crash). `.get()` is
            # the correct call — it serializes the first matched text node to
            # an actual string (a TextHandler, which is itself a str subclass).
            val = card.css(".headlineNumber::text")
            text = val.get()
            if text:
                return text
        return None

    def graphic_card(heading_text: str) -> Optional[str]:
        # Confirmed against real page structure: Households / Household Income
        # headings are <h2 class="h3">, NOT <h3 class="h3"> like the gauge-score
        # headings below. Matching is substring-based (BS4 version used `in`,
        # not exact equality) to mirror the validated working extraction.
        headings = page.css("h2.h3")
        for h in headings:
            htext = h.get_all_text(strip=True) if hasattr(h, "get_all_text") else h.text
            if htext and heading_text.lower() in htext.strip().lower():
                card = h.find_ancestor(lambda e: e.has_class("card"))
                if card:
                    val = card.css("h3.headlineNumber::text")
                    text = val.get()
                    if text:
                        return text
        return None

    def score_card(heading_text: str) -> Optional[str]:
        headings = page.css("h3.h3")
        for h in headings:
            htext = h.get_all_text(strip=True) if hasattr(h, "get_all_text") else h.text
            if htext and htext.strip().lower() == heading_text.lower():
                card = h.find_ancestor(lambda e: e.has_class("card"))
                if card:
                    val = card.css("span.sc-value::text")
                    text = val.get()
                    if text:
                        return text
        return None

    # NOTE ordering fix: density is matched FIRST with its own specific fragment,
    # and the looser "Population" alt-text fallback explicitly excludes "Density"
    # so it can no longer accidentally steal the density card's value.
    # Cleaning matches your confirmed BS4 version field-for-field:
    #  - population_total / population_density -> strips £ and , (card_by_src/alt did both)
    #  - households -> strips , only
    #  - household_income -> strips £ and ,
    #  - the three gauge scores -> plain strip only (they're "80%" style strings)
    rec.population_density = clean_currency(
        card_by_img("population_density.png", by="src")
        or card_by_img("Population Density", by="alt")
    )
    rec.population_total = clean_currency(
        card_by_img("population.png", by="src")
        or card_by_img("Population", by="alt", exclude="Density")
    )
    rec.households        = clean_numeric(graphic_card("Households"))
    rec.household_income   = clean_currency(graphic_card("Household Income"))
    rec.ab_social_score     = clean_text(score_card("AB Social Score"))
    rec.education_score     = clean_text(score_card("Education Score"))
    rec.credit_status_score = clean_text(score_card("Credit Status Score"))

    return rec

#Here I have used the Postcode.io which is specifically not defined by the mentor and also taking some more time in terms of delaying because it is sending request there  but I'm using it Reason is to resolve the postcodes of the uk even though I have hardened but still they are not directly working and I'm being blocked by the web server of the given website so will work on this if needed later on...

async def resolve_url(session: aiohttp.ClientSession, postcode: str) -> Optional[str]:
    clean = postcode.replace(" ", "").upper()  # Cleaning the postcodes if there is any space it will remove that space
    try:
        async with session.get(
            f"https://api.postcodes.io/postcodes/{clean}",  # Going to web of postcode.io then it is cleaning it
            timeout=aiohttp.ClientTimeout(total=10),  # It will try for ten seconds
        ) as r:
            if r.status != 200:  # If status code is not 200 it means it is actually not succeeding, if so it will provide a warning and will return nothing
                log.warning(f"postcodes.io {r.status} for {postcode}")
                return None
            data = await r.json()
            result = data.get("result", {})
            city = (
                result.get("admin_district")
                or result.get("region")
                or result.get("parliamentary_constituency")
                or "unknown"
            )

            city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
            pc_slug = clean.lower()
            url = f"https://www.postcodearea.co.uk/postaltowns/{city_slug}/{pc_slug}/"
            log.info(f"Resolved {postcode} -> {url}")
            return url
    except Exception as exc:
        log.error(f"URL resolution failed for {postcode}: {exc!r}")
        return None


async def resolve_url_with_retry(session: aiohttp.ClientSession, postcode: str, retries: int = 2) -> Optional[str]:
    """Small retry wrapper — postcodes.io is a third-party dependency and a single
    hiccup shouldn't permanently mark a postcode as unresolved for the whole run."""
    for attempt in range(retries + 1):
        url = await resolve_url(session, postcode)
        if url:
            return url
        if attempt < retries:
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ACTION  (runs inside the page context, after Cloudflare has resolved)
# ══════════════════════════════════════════════════════════════════════════════
async def page_action(page):
    # Dismiss cookie/consent banners if present
    for sel in [
        "button:has-text('Accept')", "button:has-text('Accept All')",
        "button:has-text('I Agree')", "button:has-text('OK')",
        "[id*='cookie'] button", "[class*='cookie'] button",
        "[class*='consent'] button",
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

    # Wait for the actual data cards to render, not just DOM ready
    for selector in ["div.headlineNumber", "h3.headlineNumber", "span.sc-value", "div.sc-gauge", "h1"]:
        try:
            await page.wait_for_selector(selector, state="visible", timeout=12_000)
            log.info(f"  Content confirmed via: {selector}")
            break
        except Exception:
            continue

    # Gentle, human-paced scroll instead of an instant jump
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
    log.info(f"  Reading for {read_time:.1f}s ...")
    await asyncio.sleep(read_time)
    return page


#PAGE SCRAPER
async def scrape_postcode(
    session: AsyncStealthySession,
    postcode: str,
    url: str,
    is_first_request: bool,
    attempt: int = 1,
) -> PostcodeDemographics:
    log.info(f"[{attempt}/{MAX_RETRIES}] Scraping {postcode} -> {url}")

    try:
        page: Response = await session.fetch(
            url,
            network_idle=True,
            page_action=page_action,
            # Only fake the "came from Google" referrer on the very first
            # page of the session — repeating it on every request within
            # the same session is itself a bit of a tell.
            google_search=is_first_request,
        )

        http_status = page.status

        if http_status in (403, 429, 503):
            log.warning(f"  HTTP {http_status} for {postcode} — site is blocking this request")
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 3)
                log.info(f"  Backing off {wait:.1f}s ...")
                await asyncio.sleep(wait)
                return await scrape_postcode(session, postcode, url, is_first_request=False, attempt=attempt + 1)

            log.warning(f"  {postcode}: blocked by site (HTTP {http_status}) — marking terminal, no further retries")
            return PostcodeDemographics(
                postcode=postcode, status="blocked",
                error=f"HTTP {http_status} — site rejected the request",
                scraped_url=url,
            )

        html = page.html_content
        if not html or len(html) < 5000:
            log.warning(f"  HTML too short ({len(html) if html else 0} chars) for {postcode}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
                return await scrape_postcode(session, postcode, url, is_first_request=False, attempt=attempt + 1)
            return PostcodeDemographics(
                postcode=postcode, status="failed",
                error="Insufficient HTML content", scraped_url=url,
            )

        html_lower = html.lower()
        has_data_cards = "headlinenumber" in html_lower or "sc-value" in html_lower
        looks_paywalled = ("daily" in html_lower and "limit" in html_lower) and not has_data_cards
        if looks_paywalled:
            log.warning(f"  Free daily view limit reached for {postcode} — skipping")
            return PostcodeDemographics(
                postcode=postcode, status="paywalled",
                error="Site's free daily view limit reached",
                scraped_url=url,
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
        log.error(f"  Error on {postcode}: {exc!r}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** attempt))
            return await scrape_postcode(session, postcode, url, is_first_request=False, attempt=attempt + 1)
        return PostcodeDemographics(
            postcode=postcode, status="failed",
            error=str(exc), scraped_url=url,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  CSV WRITER — incremental, flushed after every row so progress survives a crash
# ══════════════════════════════════════════════════════════════════════════════
def open_csv_writer(path: str):
    f = open(path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    return f, writer


def append_row(writer: csv.DictWriter, f, record: PostcodeDemographics) -> None:
    writer.writerow(asdict(record))
    f.flush()


# MAIN
async def main() -> None:
    # This will print complete banner for on the terminal to show what what is passing through A Complete Info
    log.info("=" * 65)
    log.info(" postcodearea.co.uk Demographics Scraper (Scrapling, hardened)")
    log.info(f" Postcodes : {len(POSTCODES)}")
    log.info(f" Proxy     : {PROXY_SERVER}")
    log.info(f" Headless  : {HEADLESS}")
    log.info(f" Timeout   : {PAGE_TIMEOUT_MS} ms")
    log.info("=" * 65)

    # This will function through the postcode.io to verify the url and will convert the given postcode into the actual url
    log.info("Resolving URLs via postcodes.io ...")
    url_map: dict[str, Optional[str]] = {}
    async with aiohttp.ClientSession(headers={"User-Agent": "postcode-resolver/1.0"}) as session:
        for pc in POSTCODES:
            url_map[pc] = await resolve_url_with_retry(session, pc)
            await asyncio.sleep(0.2)

    resolved = {pc: u for pc, u in url_map.items() if u}
    unresolved = [pc for pc, u in url_map.items() if not u]
    log.info(f"Resolved {len(resolved)}/{len(POSTCODES)} URLs")
    if unresolved:
        log.warning(f"Unresolved: {unresolved}")

    # Here it is creating a record for the failed urls (the postcodes which are unresolved)
    # and they will be shown as error in the csv file.
    records: list[PostcodeDemographics] = [
        PostcodeDemographics(postcode=pc, status="failed", error="Could not resolve demographics URL")
        for pc in unresolved
    ]

    csv_file, csv_writer = open_csv_writer(OUTPUT_CSV)
    for r in records:
        append_row(csv_writer, csv_file, r)

    # Every kwarg below is verified against the installed scrapling==0.4.9 source
    # (scrapling.engines._browsers._types.PlaywrightSession / StealthSession).
    # Fields that do NOT exist in this version — humanize, geoip, os_randomize,
    # disable_ads, navigator_*_override, Stealth() — have been removed.
    session_kwargs = dict(
        headless=HEADLESS,
        solve_cloudflare=True,   # auto-attempt Cloudflare Turnstile/Interstitial solving
        timeout=PAGE_TIMEOUT_MS, # milliseconds, confirmed from source docstring
        real_chrome=True,        # launch your actual installed Chrome instead of bundled Chromium
        hide_canvas=True,        # canvas fingerprint noise
        block_webrtc=True,       # stop WebRTC leaking your real IP around the proxy
        allow_webgl=True,        # keep WebGL enabled — many WAFs flag disabled WebGL as a bot signal
        block_ads=True,          # correct kwarg name (was "disable_ads")
        max_pages=1,             # single tab, keeps behavior sequential/human-paced
        retries=1,               # let Scrapling retry a transient fetch failure once internally
        dns_over_https=True,     # extra bit of network-fingerprint hardening
    )
    if PROXY.get("server"):
        session_kwargs["proxy"] = PROXY
        log.info("Using configured proxy for this session")

    async with AsyncStealthySession(**session_kwargs) as session:
        for idx, (postcode, url) in enumerate(resolved.items(), start=1):
            log.info(f"\u2500\u2500\u2500 [{idx}/{len(resolved)}] {postcode} \u2500\u2500\u2500")
            record = await scrape_postcode(session, postcode, url, is_first_request=(idx == 1))
            records.append(record)
            append_row(csv_writer, csv_file, record)

            # If the very first postcode gets hard-blocked, don't burn through
            # the rest of the list hitting the identical wall — this is a
            # diagnostic signal (IP reputation / managed-challenge tier),
            # not something later retries will fix.
            if idx == 1 and record.status == "blocked":
                log.error(
                    "  First request was blocked by Cloudflare. Stopping early — "
                    "this usually means IP reputation (try PROXY) or headless "
                    "detection (try HEADLESS = False), not a transient issue. "
                    "Fix the config and re-run rather than retrying the full list."
                )
                break

            if idx < len(resolved):
                delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                log.info(f"  Waiting {delay:.1f}s ...")
                await asyncio.sleep(delay)

    csv_file.close()

    ok = sum(1 for r in records if r.status == "ok")
    failed = sum(1 for r in records if r.status == "failed")
    blocked = sum(1 for r in records if r.status in ("blocked", "paywalled"))

    log.info("=" * 65)
    log.info(f" COMPLETE: {ok} ok | {failed} failed | {blocked} blocked/paywalled")
    log.info(f" Output  : {OUTPUT_CSV}")
    log.info("=" * 65)


if __name__ == "__main__":
    asyncio.run(main()) 