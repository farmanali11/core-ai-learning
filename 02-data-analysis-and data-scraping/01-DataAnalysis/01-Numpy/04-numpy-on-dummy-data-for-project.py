import json
import numpy as np
import collections

day7_articles = [

    {
        "title": "Iran's Football Team Triumphs in International Match","url": "https://example.com/iran-football-win",
        "source": "Sports News Daily",
        "publish_date": "2024-06-03T10:00:00Z",
        "content": "Iran's national football team secured a stunning victory against their rivals, showcasing exceptional skill and teamwork.",
        "topic": "Football",
        "sentiment_score": 0.9
    },

    {
        "title": "Iran's Football Team Triumphs in International Match",
        "url": "https://example.com/iran-football-win",
        "source": "Sports News Daily",
        "publish_date": "2024-06-03T10:00:00Z",
        "content": "Iran's national football team secured a stunning victory against their rivals, showcasing exceptional skill and teamwork.",
        "topic": "Football",
        "sentiment_score": 0.9
    },


    {
        "title": "Tensions Rise Between Iran and the US Amidst Ongoing Conflict",
        "url": "https://example.com/iran-us-tensions",
        "source": "Global News Network",
        "publish_date": "2024-06-03T12:00:00Z",
        "content": "The geopolitical situation between Iran and the United States has escalated, with both nations engaging in diplomatic confrontations.",
        "topic": "Iran-US War",
        "sentiment_score": -0.7
    },
    {
        "title": "Tensions Rise Between Iran and the US Amidst Ongoing Conflict",
        "url": "https://example.com/iran-us-tensions",
        "source": "Global News Network",
        "publish_date": "2024-06-03T12:00:00Z",
        "content": "The geopolitical situation between Iran and the United States has escalated, with both nations engaging in diplomatic confrontations.",
        "topic": "Iran-US War",
        "sentiment_score": -0.7
    }
]

day6_articles = [
    {
        "title": "Iran's Football Team Faces Tough Competition in Regional Tournament",
        "url": "https://example.com/iran-football-tournament",
        "source": "Sports News Daily",
        "publish_date": "2024-06-04T09:00:00Z",
        "content": "Iran's national football team is preparing for a challenging regional tournament, facing strong opponents from neighboring countries.",
        "topic": "Football",
        "sentiment_score": 0.8
    },
    {
        "title": "Iran-US Relations Strained Over Recent Military Exercises",
        "url": "https://example.com/iran-us-military-exercises",
        "source": "Global News Network",
        "publish_date": "2024-06-04T11:00:00Z",
        "content": "Recent military exercises conducted by the United States have led to increased tensions with Iran, raising concerns about potential conflicts.",
        "topic": "Iran-US War",
        "sentiment_score": -0.6
    }
]

day5_articles = [
    {
        "title": "Iran's Football Team Clinches Victory in Friendly Match",
        "url": "https://example.com/iran-football-friendly",
        "source": "Sports News Daily",
        "publish_date": "2024-06-05T08:00:00Z",
        "content": "In a friendly match, Iran's football team showcased their prowess, securing a win against a formidable opponent.",
        "topic": "Football",
        "sentiment_score": 0.85
    },
      {
    "title": "Iran's Football Team Clinches Victory in Friendly Match",
    "url": "https://example.com/iran-football-friendly",  
    "source": "Sports News Daily",
    "publish_date": "2024-06-05T08:00:00Z",
    "content": "In a friendly match, Iran's football team showcased their prowess, securing a win against a formidable opponent.",
    "topic": "Football",
    "sentiment_score": 0.85
    },
    {
        "title": "Iran-US War Escalates as Diplomatic Talks Fail",
        "url": "https://example.com/iran-us-war-escalation",
        "source": "Global News Network",
        "publish_date": "2024-06-05T14:00:00Z",
        "content": "Diplomatic efforts to resolve tensions between Iran and the United States have failed, leading to an escalation in hostilities.",
        "topic": "Iran-US War",
        "sentiment_score": -0.8
    },
    {
        "title": "Iran-US War Escalates as Diplomatic Talks Fail",
        "url": "https://example.com/iran-us-war-escalation",
        "source": "Global News Network",
        "publish_date": "2024-06-05T14:00:00Z",
        "content": "Diplomatic efforts to resolve tensions between Iran and the United States have failed, leading to an escalation in hostilities.",
        "topic": "Iran-US War",
        "sentiment_score": -0.8
    },
    {
        "title": "Iran-US War Escalates as Diplomatic Talks Fail",
        "url": "https://example.com/iran-us-war-escalation",
        "source": "Global News Network",
        "publish_date": "2024-06-05T14:00:00Z",
        "content": "Diplomatic efforts to resolve tensions between Iran and the United States have failed, leading to an escalation in hostilities.",
        "topic": "Iran-US War",
        "sentiment_score": -0.8
    }

  
]

day4_articles = [
    
    {
        "title": "Iran's Football Team Prepares for Upcoming International Tournament",
        "url": "https://example.com/iran-football-preparation",
        "source": "Sports News Daily",
        "publish_date": "2024-06-06T07:00:00Z",
        "content": "The Iranian football team is gearing up for an international tournament, focusing on rigorous training and strategy development.",
        "topic": "Football",
        "sentiment_score": 0.75
    },
    {
        "title": "Iran-US War: New Sanctions Imposed Amid Rising Tensions",
        "url": "https://example.com/iran-us-sanctions",
        "source": "Global News Network",
        "publish_date": "2024-06-06T13:00:00Z",
        "content": "The United States has imposed new sanctions on Iran, further straining relations and escalating the ongoing conflict.",
        "topic": "Iran-US War",
        "sentiment_score": -0.9
    },
    {
        "title": "Iran-US War: New Sanctions Imposed Amid Rising Tensions",
        "url": "https://example.com/iran-us-sanctions",
        "source": "Global News Network",
        "publish_date": "2024-06-06T13:00:00Z",
        "content": "The United States has imposed new sanctions on Iran, further straining relations and escalating the ongoing conflict.",
        "topic": "Iran-US War",
        "sentiment_score": -0.9
    }
]

day3_articles = [
    {
        "title": "Iran's Football Team Faces Setback in Qualifying Match",
        "url": "https://example.com/iran-football-setback",
        "source": "Sports News Daily",
        "publish_date": "2024-06-07T10:00:00Z",
        "content": "Iran's national football team suffered a setback in their qualifying match, facing challenges from a strong opponent.",
        "topic": "Football",
        "sentiment_score": -0.5
    },
    {
        "title": "Iran-US War: Ceasefire Talks Underway Amid Rising Casualties",
        "url": "https://example.com/iran-us-ceasefire-talks",
        "source": "Global News Network",
        "publish_date": "2024-06-07T15:00:00Z",
        "content": "Ceasefire talks between Iran and the United States have commenced, aiming to reduce casualties and find a diplomatic resolution.",
        "topic": "Iran-US War",
        "sentiment_score": -0.6
    }
] 

day2_articles = [
    {
        "title": "Iran's Football Team Wins Friendly Match Against Regional Rivals",
        "url": "https://example.com/iran-football-friendly-win",
        "source": "Sports News Daily",
        "publish_date": "2024-06-08T09:00:00Z",
        "content": "In a friendly match, Iran's football team emerged victorious against their regional rivals, boosting team morale.",
        "topic": "Football",
        "sentiment_score": 0.8
    },
]

day1_articles = [
    {
        "title": "Iran's Football Team Clinches Victory in International Friendly",
        "url": "https://example.com/iran-football-international-friendly",
        "source": "Sports News Daily",
        "publish_date": "2024-06-09T08:00:00Z",
        "content": "Iran's national football team secured a win in an international friendly match, demonstrating their competitive edge.",
        "topic": "Football",
        "sentiment_score": 0.85
    },
    {
        "title": "Iran-US War: Escalation of Conflict Raises Global Concerns",
        "url": "https://example.com/iran-us-war-escalation-global-concerns",
        "source": "Global News Network",
        "publish_date": "2024-06-09T14:00:00Z",
        "content": "The ongoing conflict between Iran and the United States has escalated, raising concerns among the international community.",
        "topic": "Iran-US War",
        "sentiment_score": -0.9
    }
]

tday_articles = [
    {
    "title": "Iran's Football Team Prepares for Upcoming International Tournament",
    "url": "https://example.com/iran-football-preparation",
    "source": "Sports News Daily",
        "publish_date": "2024-06-10T07:00:00Z",
        "content": "The Iranian football team is gearing up for an international tournament, focusing on rigorous training and strategy development.",
        "topic": "Football",
        "sentiment_score": 0.75
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
    
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
    
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
    
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    },
    {
    
        "title": "Iran-US War: International Community Calls for Immediate Ceasefire",
        "url": "https://example.com/iran-us-war-international-ceasefire",
        "source": "Global News Network",
        "publish_date": "2024-06-10T10:00:00Z",
        "content": "Amidst the escalating conflict, the international community is urging both Iran and the United States to agree to an immediate ceasefire.",
        "topic": "Iran-US War",
        "sentiment_score": -0.95
    }
  
]

total_articles = day7_articles + day6_articles + day5_articles + day4_articles + day3_articles + day2_articles + day1_articles + tday_articles

with open('news.jsonl', 'w') as f:
    for article in total_articles:
        f.write(json.dumps(article) + "\n")

articles_dicts = []

counts = collections.Counter(article["topic"] for article in total_articles)

for article in total_articles:
    articles_dicts.append({
        "title": article["title"],
        "url": article["url"],
        "source": article["source"],
        "publish_date": article["publish_date"].split("T")[0],
        "content": article["content"],
        "topic": article["topic"],
        "sentiment_score": article["sentiment_score"]
    })

counts = {}
for article in articles_dicts:
  key = article["topic"],article["publish_date"]
  counts[key] = counts.get(key, 0) + 1

dates_in_order = ["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06", "2024-06-07", "2024-06-08", "2024-06-09", "2024-06-10"]

football_counts = []

for date in dates_in_order:
    key = ("Football", date)
    football_counts.append(counts[key])
iran_us_war_counts = []
for date in dates_in_order:
    key = ("Iran-US War", date)
    iran_us_war_counts.append(counts.get(key, 0))

def check_spike(counts_list):
    history = counts_list[:7]
    today_count = counts_list[7]
    mean_7d = np.mean(history)
    std_7d = np.std(history)
    threshold = mean_7d + 2 * std_7d
    is_spike = today_count > threshold
    return mean_7d, std_7d, threshold, today_count,is_spike

print("Football Spike Check:")
football_mean, football_std, football_threshold, football_today_count, football_is_spike = check_spike(football_counts)

iran_us_war_mean, iran_us_war_std, iran_us_war_threshold, iran_us_war_today_count, iran_us_war_is_spike = check_spike(iran_us_war_counts)
print(f"Mean: {iran_us_war_mean}, Std: {iran_us_war_std}, Threshold: {iran_us_war_threshold}, Today's Count: {iran_us_war_today_count}, Is Spike: {iran_us_war_is_spike}")

def average_sentiment(articles,topic):
    sentiment_score = [article["sentiment_score"] for article in articles if article["topic"] == topic]
    return np.mean(sentiment_score) if sentiment_score else 0

topic_names = ["Football", "Iran-US War"]
topic_data = {
    "Football":football_counts,
    "Iran-US War":iran_us_war_counts
}

topic_summaries =[]
for topic in topic_names:
    mean,std, threshold,today_count,is_spike = check_spike(topic_data[topic])
    average_sentiment_score = average_sentiment(articles_dicts, topic)
    summary = {
        "topic": topic,
        "today_count": today_count,
        "mean_7d": mean,
        "std_7d": std,
        "threshold": threshold,
        "is_spike": is_spike,
        "average_sentiment": average_sentiment_score
    }
    topic_summaries.append(summary)

    topic_summaries = sorted(topic_summaries, key=lambda x: x["today_count"], reverse=True)

print("Top Trending Topics:")
for i,summary in enumerate(topic_summaries[:5],start=1):
    print(f"{i}. {summary['topic']} — Mentions today: {summary['today_count']} | Spike {summary['is_spike']} | Average Sentiment: {summary['average_sentiment']:.2f}")