from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import Stealth
import random

class StealthBrowser:
    """
    Drop-in stealth browser factory.
    Usage:
        async with StealthBrowser() as sb:
            page = await sb.new_page()
            await page.goto("https://example.com")
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    VIEWPORTS = [
        {"width": 1366, "height": 768},
        {"width": 1920, "height": 1080},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
    ]

    def __init__(
        self,
        headless: bool = True,
        proxy: dict = None,       # {"server": "http://ip:port"}
        locale: str = "en-US",
        timezone: str = "America/New_York",
        randomize: bool = True,   # randomise UA + viewport each time
    ):
        self.headless = headless
        self.proxy = proxy
        self.locale = locale
        self.timezone = timezone
        self.randomize = randomize
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        self._pw_ctx = Stealth().use_async(async_playwright())
        self._playwright = await self._pw_ctx.__aenter__()

        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            proxy=self.proxy,
        )
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        await self._pw_ctx.__aexit__(*args)

    async def new_page(self, url: str = None):
        ua = (random.choice(self.USER_AGENTS) if self.randomize
              else self.USER_AGENTS[0])
        vp = (random.choice(self.VIEWPORTS) if self.randomize
              else self.VIEWPORTS[0])

        context: BrowserContext = await self._browser.new_context(
            user_agent=ua,
            viewport=vp,
            locale=self.locale,
            timezone_id=self.timezone,
            color_scheme="light",
            device_scale_factor=1,
            extra_http_headers={
                "Accept-Language": f"{self.locale},{self.locale[:2]};q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
            },
        )

        # Apply custom patches on top of stealth
        await context.add_init_script("""
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            Object.defineProperty(window, 'outerWidth', {
                get: () => window.innerWidth
            });
            Object.defineProperty(window, 'outerHeight', {
                get: () => window.innerHeight + 88
            });
        """)

        page = await context.new_page()
        if url:
            await page.goto(url)
        return page


# ── Usage example ──────────────────────────────────────────
async def main():
    async with StealthBrowser(headless=True, randomize=True) as sb:
        page = await sb.new_page("https://bot.sannysoft.com")
        await page.screenshot(path="factory_test.png", full_page=True)
        print("Done — check factory_test.png")

    await (main())



# Save stealth_factory.py in your project root and import it everywhere:
# from stealth_factory import StealthBrowser

# async with StealthBrowser(headless=True) as sb:
#     page = await sb.new_page("https://yoursite.com")
#     # All your normal Playwright code here