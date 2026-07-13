import asyncio
from parser import parse_bbcnews_articles,parse_radiopakistan_articles,parse_geonews_articles
from datetime import date
import logging
from fetcher import fetch_with_fallback
import time
import json
import yaml

from analyzer import build_report,plot_spikes

from writer import write_articles

output_path = f"data/news_{date.today().isoformat()}.jsonl"

async def worker(queue, output_path, lock,seen_urls):

    while True:
        url = await queue.get()
        try:
            html = await fetch_with_fallback(url)
            if "geo.tv" in url:
                articles = parse_geonews_articles(html)
            elif "bbc.com" in url:
                articles = parse_bbcnews_articles(html)
            else:
                articles = parse_radiopakistan_articles(html)
            await write_articles(articles,output_path,lock,seen_urls)

        except Exception as e:
            logging.error(f"Worker failed on {url}: {e}")
        finally:
            queue.task_done()


def load_config(path="logs/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

def load_seen_urls(output_path):
    seen = set()
    try:
        with open(output_path,"r") as f:
            for line in f:
                article = json.loads(line)
                seen.add(article["url"])
    except FileNotFoundError:
        pass

    return seen

config = load_config()
setup_logging(config["paths"]["log_file"])
sleep_seconds = config["pipeline"]["run_interval_minutes"] * 60
async def main():
    logging.info("TrendPulse starting up")
    queue = asyncio.Queue()
    lock = asyncio.Lock()
    for url in config["urls"]:
        await queue.put(url)

    seen_urls = load_seen_urls(output_path)
    tasks = [asyncio.create_task(worker(queue, output_path, lock,seen_urls)) for _ in range(10)]
    await queue.join()

    for task in tasks:
        task.cancel()
    logging.info("Scrapping Complete,running Analysis")

    report = await asyncio.to_thread(build_report)
    if report.empty:
        logging.warning("No Data Available to Analyze")
    else:
        await asyncio.to_thread(plot_spikes, report)
        top_topic = report.iloc[0]["topic"]
        top_mentions = report.iloc[0]["today"]
        logging.info(f"Chart saved. Top topic: {top_topic} ({top_mentions} mentions)")

    print("Done for data", output_path)


while True:
    try:
        asyncio.run(main())
        time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        print("\nProcess is Interrupted by the User.\nCancelling...")
        break
print("Program exited Successfully...")
