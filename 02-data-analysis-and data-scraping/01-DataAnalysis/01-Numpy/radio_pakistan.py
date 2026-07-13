from bs4 import BeautifulSoup

def parse_radiopakistan_articles(html):
  soup = BeautifulSoup(html,'html.parser')

  cards = soup.select("div.card.h-100")


  all_articles = []

  for card in cards:
    title = card.find("h5",class_="card-title").get_text(strip=True)
    link_tag = card.find("a")
    url = link_tag["href"]

    content = card.find("p",class_="card-text").get_text(strip=True)

    published_at = url.split("/")[1]

    source = "Radio Pakistan"

    article = {
    "title":title,
    "url":url,
    "content":content,
    "source":source,
    "published_at":published_at,
  }

    all_articles.append(article)
  return all_articles



