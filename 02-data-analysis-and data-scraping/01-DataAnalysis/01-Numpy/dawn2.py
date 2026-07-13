from bs4 import BeautifulSoup
import requests
import json

url = "https://www.dawn.com/latest-news"

def parse_dawn_articles(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.find_all("article", class_="story")

    all_articles = []

    for article in articles:
        title_tag = article.find("h2", class_="story__title")
        if not title_tag:
            continue
        link_tag = title_tag.find("a")
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        article_url = link_tag["href"]

        excerpt_tag = article.find("div", class_="story__excerpt")
        content = excerpt_tag.get_text(strip=True) if excerpt_tag else ""

        time_tag = article.find("span", class_="timestamp--time")
        published_at = time_tag["datetime"].split("T")[0] if time_tag and time_tag.has_attr("datetime") else ""

    return all_articles

    response = requests.get(url)
    articles = parse_dawn_articles(response.text)

    print(f"Parsed {len(articles)} articles\n")
    print("=" * 60)

    for i, a in enumerate(articles, start=1):
        print(f"\nArticle #{i}")
        print(json.dumps(a, indent=2, ensure_ascii=False))
        print("-" * 60)