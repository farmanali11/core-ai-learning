from bs4 import BeautifulSoup

TOPIC_KEYWORDS = {
    "Politics": ["Shabaz Sharif","Primer Minister", "minister", "cabinet", "president", "parliament", "election"],
    "Sports": ["India-England","cricket", "football", "world cup", "match", "tournament"],
    "Conflict": ["Donald Trump","Iran-US","war", "attack", "strike", "military", "killed", "clash"],
    "Economy": ["tax", "economy", "trade", "investment", "market", "revenue"],
}
def classify_topic(title, content):
    text = (title + " " + content).lower()

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return topic
    return "General"

POSITIVE_WORDS = ["win", "success", "growth", "agree", "celebrate", "victory", "boost"]
NEGATIVE_WORDS = ["killed", "attack", "crisis", "war", "death", "collapse", "conflict"]

def score_sentiment(title, content):
    text = (title + " " + content).lower()

    pos = sum(text.count(w) for w in POSITIVE_WORDS)
    neg = sum(text.count(w) for w in NEGATIVE_WORDS)

    total = pos + neg

    if total == 0:
        return 0.0
    return (pos - neg) / total

def parse_geonews_articles(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", attrs={"data-vr-contentbox-url": True})

    all_articles = []

    for card in cards:
        title_tag = card.find("h1", attrs={"data-vr-headline": True})
        if not title_tag:
            title_tag = card.find("h2", attrs={"data-vr-headline": True})

        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        article_url = card["href"]
        if not article_url:
            continue
        content = ""
        published_at_tag = card.find("span", class_="date")
        if not published_at_tag:
            continue
        published_at = published_at_tag.get_text(strip=True)
        source = "Geo News"
        article_data = {
            "title": title,
            "url": article_url,
            "content": content,
            "source": source,
            "published_at": published_at,
            "topic": classify_topic(title, content),
            "sentiment_score": score_sentiment(title, content),
        }
        all_articles.append(article_data)
    return all_articles


def parse_bbcnews_articles(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", attrs={"data-indexcard": "true"})

    all_articles = []

    for card in cards:
        title_tag = card.find("h2", attrs={"data-testid": "card-headline"})
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link_tag = card.find("a")
        if not link_tag:
            continue
        article_url = link_tag["href"]
        if not article_url:
            continue
        content_tag = card.find("p", attrs={"data-testid": "card-description"})
        if not content_tag:
            continue
        content = content_tag.get_text(strip=True)
        published_at_tag = card.find(
            "span", attrs={"data-testid": "card-metadata-lastupdated"}
        )
        if not published_at_tag:
            continue
        published_at = published_at_tag.get_text(strip=True)

        source = "BBC News"

        article_data = {
            "title": title,
            "url": article_url,
            "content": content,
            "source": source,
            "published_at": published_at,
            "topic": classify_topic(title, content),
            "sentiment_score": score_sentiment(title, content),
        }

        all_articles.append(article_data)
    return all_articles

def parse_radiopakistan_articles(html):
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.card.h-100")

    all_articles = []

    for card in cards:
        title = card.find("h5", class_="card-title").get_text(strip=True)
        link_tag = card.find("a")
        url = link_tag["href"]

        content = card.find("p", class_="card-text").get_text(strip=True)

        published_at = url.split("/")[1]

        source = "Radio Pakistan"

        article = {
            "title": title,
            "url": url,
            "content": content,
            "source": source,
            "published_at": published_at,
            "topic": classify_topic(title, content),
            "sentiment_score": score_sentiment(title, content),
        }
        all_articles.append(article)
    return all_articles
