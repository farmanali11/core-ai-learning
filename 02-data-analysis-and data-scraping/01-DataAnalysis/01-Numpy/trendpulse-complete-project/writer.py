import aiofiles
import json

async def write_articles(articles,output_path,lock,seen_urls):
     async with lock:
          async with aiofiles.open(output_path, "a", encoding="utf-8") as f:
               for article in articles:
                    if article["url"] not in seen_urls:                 
                      await f.write(json.dumps(article) + "\n")
                      seen_urls.add(article["url"])

