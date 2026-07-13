import pandas as pd
import numpy as np
import glob
import os
import matplotlib
matplotlib.use("Agg")


import matplotlib.pyplot as plt

def load_all_data(data_dir="data"):
    files = glob.glob(f"{data_dir}/news_*.jsonl")
    all_dfs = []
    for file in files:
        day = os.path.basename(file).replace("news_", "").replace(".jsonl", "")
        df = pd.read_json(file, lines=True)
        df["day"] = day
        all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True)


def get_daily_counts(df):
    counts = df.groupby(["topic", "day"]).size().reset_index(name="mentions")
    return counts

def compute_spikes(counts, window=7, k=2):
    counts = counts.sort_values(["topic", "day"])
    results = []
    for topic, group in counts.groupby("topic"):
        group = group.reset_index(drop=True)
        history = group["mentions"][:-1]
        today = group["mentions"].iloc[-1] if len(group) > 0 else 0
        mean = history.mean() if len(history) > 0 else 0
        std = history.std() if len(history) > 0 else 0
        threshold = mean + k * std
        has_history = len(history) >=1
        is_spike = today > threshold if has_history else False
        results.append(
            {
                "topic": topic,
                "today": today,
                "mean": mean,
                "std": std,
                "threshold": threshold,
                "is_spike": is_spike,
            }
        )
    return pd.DataFrame(results)

def get_avg_sentiment(df):
    return df.groupby("topic")["sentiment_score"].mean().reset_index()


def build_report(data_dir="data"):
    df = load_all_data(data_dir)
    counts = get_daily_counts(df)
    spikes = compute_spikes(counts)
    sentiment = get_avg_sentiment(df)
    report = spikes.merge(sentiment, on="topic")
    return report.sort_values("today", ascending=False)

def plot_spikes(report, output_path="charts/spike_chart.png"):
    fig, ax = plt.subplots()
    colors = ["r" if spike else "b" for spike in report["is_spike"]]
    ax.bar(report["topic"], report["today"], color=colors)
    ax.set_ylabel("Mentions today")
    ax.set_title("Topic Mentions vs Spike Threshold")
    plt.tight_layout()
    plt.savefig(output_path,dpi=2000)