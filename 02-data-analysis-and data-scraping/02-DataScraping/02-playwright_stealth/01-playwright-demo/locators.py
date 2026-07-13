from playwright.async_api import page.async
await page.get_by_label( "User Name").fill()



await page.get_by_role("button",name , re.compile("submit",re.IGNORECASE)).click()



page_one = await context.new_page()

page_two = await context.new_page()

all_page =context.pages



async def handle_pages(page):
  await page.wait_for_load_state()
  print(await page.title())
