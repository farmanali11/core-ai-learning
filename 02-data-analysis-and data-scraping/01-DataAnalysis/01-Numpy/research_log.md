# Research Log — NewsSentimentAggregator

## 2026-07-06 — Day 1: Fake data + numpy analyzer (Requirements 4 & 5)

### Goal
Build and verify the analysis/reporting half of the pipeline (spike detection +
sentiment + trending report) using hand-crafted fake data, before touching any
real scraping. No AI-written code — self-implemented, guided by questions only.

### Schema decided
Article-level records (not pre-aggregated), matching the real scraper's future
output:
- title (string)
- url (string)
- source (string)
- publish_date (ISO datetime string, e.g. "2024-06-03T10:00:00Z")
- content (string)
- topic (string)
- sentiment_score (float, -1.0 to 1.0)

Rationale: aggregated daily counts would've been easier, but article-level data
is what the real scraper will actually produce, and it forces practice on the
grouping/counting step that's otherwise skipped.

### Fake dataset
2 topics: "Football" (flat/normal) and "Iran-US War" (spikes today).
7 history days + 1 "today", counts per table:

| Day   | Football | Iran-US War |
|-------|----------|-------------|
| 7     | 2        | 2           |
| 6     | 1        | 1           |
| 5     | 2        | 3           |
| 4     | 1        | 2           |
| 3     | 1        | 1           |
| 2     | 1        | 0           |
| 1     | 1        | 1           |
| Today | 1        | 10          |

Total articles: 30 (verified by count after JSONL write).

### Mistakes made and fixed (important — re-read before next task)
1. Dates were initially in reverse chronological order (Day 7 = most recent
   instead of oldest). Fixed by re-deriving all 8 dates so they increase from
   Day 7 → Today.
2. Iran-US War history originally had an outlier (14) buried inside the
   7-day history window instead of as "today" — this would have inflated
   std enough that the real spike (today) wouldn't have crossed the
   threshold. Lesson: outliers must be placed deliberately, and history
   should be verified as "boring" before trusting a spike test.
3. Article counts didn't match the hand-built table in a couple of places
   (Day 1 Football, Today's totals) — caught by explicitly predicting counts
   before running code, not after.
4. Two "today" articles had a leftover wrong date (copy-paste error, pointed
   to Day 4's date instead of Today's) — would have silently miscounted
   during grouping. Caught by checking every article's date against its
   intended day, not just trusting the file compiled without errors.
5. `enumerate(list, start=[1])` — passed a list instead of an int by
   accident (typo'd brackets). Diagnosed correctly by reading the traceback's
   last line first, per the "error-first reading" protocol.

### Verified logic built (self-written, each step predicted before running)
- JSONL write/read round-trip (30 articles, confirmed count).
- Date extraction: `publish_date.split("T")[0]` to strip time from ISO string.
- Grouping by (topic, date) using tuple dict keys:
  `key = article["topic"], article["publish_date"]`
- Per-topic ordered count lists (history[0:7] + today[7]) built by iterating
  a known ordered date list and looking up counts.
- `check_spike(counts_list)`: mean/std of history via numpy, threshold =
  mean + 2*std, spike = today > threshold.
  - Football: mean≈1.29, std≈0.45, threshold≈2.19, today=1 → No spike ✓
  - Iran-US War: mean≈1.43, std≈0.90, threshold≈3.24, today=10 → Spike ✓
- `average_sentiment(articles, topic)`: filter by topic, np.mean, guarded
  against empty list.
  - Football ≈ 0.695
  - Iran-US War ≈ -0.86
- Final report: built list of per-topic summary dicts, sorted descending by
  today_count, printed top N with formatted floats (`:.2f`).

### Output (final, verified)
Top Trending Topics:

Iran-US War — Mentions today: 10 | Spike: True | Avg Sentiment: -0.86
Football — Mentions today: 1 | Spike: False | Avg Sentiment: 0.70

### Status
Requirements 4 & 5 (analysis + reporting) — DONE, self-verified end to end.

### Next up
Requirements 1–3: real fetching (aiohttp for static, playwright-stealth for
JS/anti-bot), parsing (bs4/Playwright/Scrapling), and the asyncio queue +
10 workers + aiofiles JSONL writer. Plan: isolate fetch on one static site
first, then one JS-heavy site, before touching the queue at all. Check
robots.txt for every target site before writing any scraper for it. q