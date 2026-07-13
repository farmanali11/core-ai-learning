import asyncio
import random
import math
from playwright.async_api import async_playwright, Page

# Common character pairs typed quickly by humans
FAST_BIGRAMS = {
    'th', 'he', 'in', 'er', 'an', 'on', 're', 'en', 
    'at', 'es', 'or', 'te', 'ng', 'is', 'ti', 'ar'
}

class HumanPage:
    """
    A human simulation layer wrapping Playwright page actions.
    Use this class instance instead of raw page interactions to bypass detection.
    """
    def __init__(self, page: Page):
        self.page = page

    async def think(self, min_s: float = 0.5, max_s: float = 2.0):
        """Simulate a short burst of cognitive pause."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def read_page(self, min_s: float = 2.0, max_s: float = 5.0):
        """Simulate the user reading content on the screen."""
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def move_mouse_to(self, tx: float, ty: float, steps: int = 30):
        """Move the mouse to target coordinates using a natural Bezier curve."""
        # Generate random start and control points for a smooth curve
        sx = random.randint(100, 900)
        sy = random.randint(100, 600)
        cp1x = sx + random.randint(-200, 200)
        cp1y = sy + random.randint(-150, 150)
        cp2x = tx + random.randint(-80, 80)
        cp2y = ty + random.randint(-80, 80)

        for i in range(steps + 1):
            t = i / steps
            # Cubic Bezier equation
            x = ((1-t)**3 * sx + 3 * (1-t)**2 * t * cp1x + 3 * (1-t) * t**2 * cp2x + t**3 * tx)
            y = ((1-t)**3 * sy + 3 * (1-t)**2 * t * cp1y + 3 * (1-t) * t**2 * cp2y + t**3 * ty)
            
            # Sinusoidal slowing down at the start and end of movement
            sf = math.sin(t * math.pi)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.008, 0.03) / (sf + 0.1))

    async def click(self, selector: str):
        """Find an element, smoothly move to it with a random offset, and click."""
        el = await self.page.wait_for_selector(selector, timeout=10000)
        box = await el.bounding_box()
        if not box:
            raise ValueError(f"Element with selector '{selector}' has no bounding box.")
            
        # Target center with a slight random human variance
        tx = box["x"] + box["width"]/2 + random.uniform(-4, 4)
        ty = box["y"] + box["height"]/2 + random.uniform(-3, 3)
        
        await self.move_mouse_to(tx, ty)
        await asyncio.sleep(random.uniform(0.05, 0.18))
        
        # Simulate click duration variance
        await self.page.mouse.down()
        await asyncio.sleep(random.uniform(0.04, 0.12))
        await self.page.mouse.up()
        
        await asyncio.sleep(random.uniform(0.1, 0.35))

    async def type(self, selector: str, text: str):
        """Type text with realistic speed variance, bigram timing, and typos."""
        await self.click(selector)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        i = 0
        while i < len(text):
            char = text[i]
            bigram = text[i:i+2].lower() if i+1 < len(text) else ""
            
            # 3% chance of a typo on letters
            if random.random() < 0.03 and char.isalpha():
                typo = random.choice('qwertyuiopasdfghjklzxcvbnm')
                await self.page.keyboard.type(typo)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await self.page.keyboard.press('Backspace')
                await asyncio.sleep(random.uniform(0.05, 0.12))
                
            await self.page.keyboard.type(char)
            
            # Assign delays based on specific character configurations
            if char == ' ':
                delay = random.uniform(0.07, 0.16)
            elif char in '.,!?;:':
                delay = random.uniform(0.12, 0.30)
            elif char == '\n':
                delay = random.uniform(0.20, 0.50)
            elif bigram in FAST_BIGRAMS:
                delay = random.uniform(0.03, 0.08)
            else:
                delay = random.uniform(0.06, 0.15)
                
            # Occasional cognitive hesitation pause while typing
            if random.random() < 0.015:
                delay += random.uniform(0.4, 1.0)
                
            await asyncio.sleep(delay)
            i += 1

    async def scroll(self, direction: str = "down", distance: int = None, read_pause: bool = True):
        """Scroll in chunks with micro-pauses and optional reading rests."""
        if distance is None:
            distance = random.randint(300, 800)
            
        sign = 1 if direction == "down" else -1
        scrolled = 0
        
        while scrolled < distance:
            chunk = min(random.randint(60, 180), distance - scrolled)
            await self.page.mouse.wheel(0, sign * chunk)
            scrolled += chunk
            await asyncio.sleep(random.uniform(0.04, 0.14))
            
            # Intermittent pauses mid-scroll
            if read_pause and random.random() < 0.2:
                await asyncio.sleep(random.uniform(0.6, 2.0))
                
        if read_pause:
            await asyncio.sleep(random.uniform(0.4, 1.2))

    async def idle_move(self, duration: float = 3.0):
        """Simulate micro mouse jitters and drifting when a human is idling."""
        end = asyncio.get_event_loop().time() + duration
        x, y = random.randint(200, 700), random.randint(150, 450)
        
        while asyncio.get_event_loop().time() < end:
            x = max(50, min(x + random.randint(-25, 25), 1300))
            y = max(50, min(y + random.randint(-15, 15), 700))
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.35))


# =====================================================================
# EXAMPLE USAGE
# =====================================================================
async def main():
    async with async_playwright() as p:
        # Launch browser (use headless=False to visually watch the human-like behavior)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        raw_page = await context.new_page()
        
        # Instantiate your human simulation layer
        human_page = HumanPage(raw_page)
        
        # Navigate to a website
        await raw_page.goto("https://google.com")
        
        # Perform human-like actions
        await human_page.think(1.0, 2.5)
        
        # Use selector matching your target page
        search_input = "textarea[name='q']"
        await human_page.type(search_input, "Playwright stealth web scraping strategies")
        await raw_page.keyboard.press("Enter")
        
        # Wait for page updates, then scroll down like a reader
        await raw_page.wait_for_load_state("networkidle")
        await human_page.scroll(direction="down", distance=600)
        await human_page.idle_move(duration=2.0)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
