from bs4 import BeautifulSoup
import requests
import json

def parse_geonews_articles(html):
  soup = BeautifulSoup(html,'html.parser')
  cards = soup.find_all("a", attrs={"data-vr-contentbox-url": True})


  all_articles = []

  for card in cards:
    title_tag = card.find("h1",attrs={"data-vr-headline":True})
    if not title_tag:
      title_tag = card.find("h2",attrs={"data-vr-headline":True})

    if not title_tag:
      continue
    title = title_tag.get_text(strip=True)
    article_url = card["href"] 
    if not article_url:
      continue
    content =""
    published_at_tag = card.find("span",class_ ="date")
    if not published_at_tag:
      continue
    published_at = published_at_tag.get_text(strip=True)
    source = "Geo News"
    article_data = {
    "title":title,
    "url":article_url,
    "content":content,
    "source":source,
    "published_at":published_at,
  }
    all_articles.append(article_data)
  return all_articles