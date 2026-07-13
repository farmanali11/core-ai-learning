import asyncio
from radio_pakistan import parse_radiopakistan_articles
from dawn2 import parse_dawn_articles
from bbc_news import parse_bbcnews_articles
from geo_news import parse_geonews_articles
from fetch_html import fetch_html
from datetime import date
import time
import aiofiles
import json

output_path = f"data/news_{date.today().isoformat()}.jsonl"
async def worker(queue,output_path,lock):

  while True:
    url = await queue.get()
    try:
      html = await fetch_html(url)
      if "geo.tv" in url:
        articles = parse_geonews_articles(html)
      elif "bbc.com" in url:
        articles = parse_bbcnews_articles(html)
      else:
        articles = parse_radiopakistan_articles(html)

      async with lock:
        async with aiofiles.open(output_path,"a",encoding='utf-8') as f:
          for article in articles:
            await f.write(json.dumps(article) + "\n")
    except Exception as e:
      print(f"Worker failed on {url}: {e}")
    finally:
      queue.task_done()

async def main():
  queue = asyncio.Queue()
  lock = asyncio.Lock()

  await queue.put("https://www.radio.gov.pk/newslist/1")
  await queue.put("https://www.geo.tv/latest-news")
  await queue.put("https://www.bbc.com/news")

  tasks = [asyncio.create_task(worker(queue,output_path,lock)) for _ in range(10) ]
  await queue.join()
  for task in tasks:
    task.cancel()

  print("Done for data",output_path)

while True:
  asyncio.run(main())
  time.sleep(3600)
