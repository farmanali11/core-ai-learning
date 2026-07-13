# from playwright.sync_api import sync_playwright

# with sync_playwright() as p:
#         # Launch the browser
#         browser = p.chromium.launch(headless=False)
#         page = browser.new_page()
        
#         # Navigate to Google
#         page.goto("https://google.com")
        
#         # Get and print the title
#         title = page.title()
#         print(f"Page Title: {title}")
        
#         # Close the browser
#         browser.close()


import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 1. Launch browser and open a fresh page
    print("Launching browser...")
    browser = p.chromium.launch(headless=False)  # Keep False so you can watch it work
    page = browser.new_page()
    
    # 2. Navigate and wait for the page to load fully
    print("Navigating to Google...")
    page.goto("https://www.google.com")
    
    # 3. Handle cookie consent banners automatically if they appear
    # (Playwright will skip this if the button isn't visible)
    if page.get_by_role("button", name="Accept all").is_visible():
        page.get_by_role("button", name="Accept all").click()
    
    # 4. Locate the search box, fill it, and press Enter
    print("Searching for 'Playwright automation tool'...")
    search_box = page.get_by_role("combobox", name="Search")
    search_box.fill("Playwright automation tool")
    time.sleep(3)
    search_box.press("Enter")
    
    # 5. Wait for the search results page to load
    page.wait_for_selector("#search")
    
    # 6. Extract and print the titles of the top search results
    print("\n--- Top Search Results Found ---")
    results = page.locator("#search h3").all()
    for index, result in enumerate(results[:5], start=1):
        print(f"{index}. {result.inner_text()}")
        
    # 7. Click on the first search result link
    print("\nClicking on the first result...")
    results[0].click()
    
    # 8. Wait for the new website to load and capture a screenshot
    page.wait_for_load_state("networkidle")
    print(f"Now on page: {page.title()}")
    
    screenshot_path = "playwright_success.png"
    page.screenshot(path=screenshot_path)
    print(f"Saved a screenshot to: {screenshot_path}")
    
    # 9. Clean up and close
    print("Closing browser in 3 seconds...")
    time.sleep(3)
    browser.close()
