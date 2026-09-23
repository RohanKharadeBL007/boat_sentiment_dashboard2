# boAt Sentiment & Theme Analysis Dashboard

AI for Business project — sentiment and theme analysis of boAt customer
feedback across Play Store, e-commerce (Amazon/Flipkart), and social
(Reddit/Twitter) sources.

## Project structure

```
boat_sentiment_dashboard/
├── scrapers/
│   ├── playstore_scraper.py      # boAt app reviews (google-play-scraper)
│   ├── ecommerce_scraper.py      # Amazon/Flipkart reviews (Selenium)
│   └── social_scraper.py         # Reddit (PRAW) + Twitter (snscrape)
├── pipeline/
│   ├── preprocessing.py          # cleaning, merging sources
│   ├── sentiment_analysis.py     # VADER + optional transformer
│   └── topic_modeling.py         # LDA + optional BERTopic
├── dashboard/
│   └── app.py                    # Streamlit dashboard
├── data/                         # raw + sample scraped CSVs go here
├── outputs/                      # processed CSVs land here
├── run_pipeline.py               # ties preprocessing -> sentiment -> topics together
└── requirements.txt
```

## IMPORTANT: where to run what

This was scaffolded and tested in a sandboxed environment that cannot reach
Amazon, Flipkart, Play Store, or Twitter/Reddit directly. That means:

- **Scrapers** (`scrapers/*.py`) — run these on your own laptop with normal
  internet access.
- **Pipeline + dashboard** (`pipeline/`, `run_pipeline.py`, `dashboard/app.py`)
  — already tested and working end-to-end on a 30-row sample dataset
  (`data/sample_reviews.csv`), so you know the logic is correct. You just
  need to swap in your real scraped data.

## Quickest way to run everything locally

```bash
pip install -r requirements.txt
./start_local.sh            # dry-run: uses existing data/*.csv, then opens the dashboard
./start_local.sh --live     # actually scrapes playstore + amazon + reddit first
./start_local.sh --watch    # also re-runs the pipeline automatically every hour in the background
```

Windows: `start_local.bat` (dry-run only, or `start_local.bat --live`).

This runs the full pipeline once (scrape → clean → sentiment → topics →
GenAI executive summary) and then launches the dashboard as a live local
webapp at **http://localhost:8501**. The dashboard always shows whatever
the most recent pipeline run produced — no manual file copying.

## Running it as a fully automated system

The system is designed to run unattended end to end via `orchestrator.py`:

```text
scrape (per source, fault-isolated)
   -> merge & clean
   -> sentiment (VADER / transformer)
   -> topic modeling (LDA)
   -> GenAI executive summary (Claude or Gemini)
   -> outputs/processed_reviews_latest.csv + executive_summary_latest.txt
   -> dashboard auto-reads the latest run, no manual file swapping
```

Every stage is wrapped so one failure (e.g. Twitter scraping gets blocked,
or an LLM API call times out) logs the error and the run continues with
whatever data/results it has — it never hard-crashes an automated run.

**Run once, live:**
```bash
python orchestrator.py --sources playstore amazon reddit
```

**Run on autopilot** (foreground loop, daily or hourly):
```bash
python orchestrator.py --schedule daily
```

**Dry run** (skips scraping, reuses whatever CSVs are already in `data/` —
useful for CI, or testing the analysis+GenAI layers without hitting live sites):
```bash
python orchestrator.py --dry-run
```

All runs are logged to `logs/orchestrator.log`, and each run's processed
data + AI-generated executive summary are timestamped in `outputs/`, with
`_latest` copies the dashboard always reads automatically.

### GenAI insight agent

Set `ANTHROPIC_API_KEY` (or `GOOGLE_API_KEY`) as an environment variable
(see `.env.example`) and the orchestrator will call Claude/Gemini to turn
the sentiment+theme stats into a real executive summary. Without a key,
it automatically falls back to a rule-based summary so the pipeline never
breaks — but set a key before your final submission so the report reflects
genuine GenAI synthesis (this is your course's Generative AI module output).

### Optional: GitHub Actions (only if you want cloud scheduling later)

`.github/workflows/run_pipeline.yml` is included but not required — the
project is designed to run entirely on your own machine via
`start_local.sh`. If you later want the pipeline to also refresh in the
cloud on a schedule, this workflow reprocesses whatever CSVs are
committed to `data/` and commits the refreshed `outputs/` back
automatically; it needs an `ANTHROPIC_API_KEY` repo secret to generate
real GenAI summaries in CI. Safe to ignore entirely for local use.

## Setup

```bash
pip install -r requirements.txt
```

You don't need every package — install per source:
- Play Store only: `google-play-scraper`
- Amazon/Flipkart: `selenium webdriver-manager` + Chrome installed
- Reddit: `praw` (needs a free Reddit API app — see script docstring)
- Twitter/X: `snscrape` (increasingly unreliable as X blocks scraping —
  have a fallback plan, e.g. lean more on Reddit if this fails)

## Step-by-step

1. **Scrape** each source on your own machine:
   ```bash
   cd scrapers
   python playstore_scraper.py
   python ecommerce_scraper.py --product_url "<amazon review page url>" --pages 10
   python social_scraper.py
   ```
   Each saves a CSV into `data/`.

2. **Run the pipeline** to merge, clean, score sentiment, and extract topics:
   ```bash
   python run_pipeline.py --inputs data/playstore_reviews.csv data/amazon_reviews.csv data/reddit_mentions.csv --n_topics 6
   ```
   - Use `--min_df 2` if your merged corpus is small (a few hundred rows);
     the default `--min_df 5` is tuned for thousands of reviews.
   - Use `--sentiment_method transformer` for higher accuracy at the cost
     of speed (needs `transformers` + `torch`).

3. **Launch the dashboard**:
   ```bash
   cd dashboard
   streamlit run app.py
   ```
   Update `DATA_PATH` at the top of `app.py` to point at your real
   `outputs/processed_reviews.csv` once you have it (it currently points
   at the sample file for demo purposes).

## Known limitations / things to improve before final submission

- **VADER sentiment** is fast but lexicon-based — it can misread reviews
  with mixed-signal words (e.g. "amazing" inside an otherwise negative
  sentence). Consider re-scoring at least the 1-star/5-star subset with
  the transformer option for accuracy, or running both and comparing.
- **LDA topics** need a reasonably large, clean corpus (aim for at least a
  few hundred reviews per source) to produce distinct, non-overlapping
  themes — on the 30-row test sample topics overlap somewhat. BERTopic
  will likely produce cleaner themes once you have real volume, at the
  cost of longer runtime.
- **Amazon/Flipkart scraping** may break due to selector changes or
  anti-bot measures — check the fallback note in `ecommerce_scraper.py`
  about using a pre-scraped Kaggle dataset if this becomes a blocker.
- **Twitter scraping via snscrape** has become unreliable since X locked
  down its platform; don't rely on this being your primary social source.

## Next steps for the group

- [ ] Decide final scope: which specific boAt product line(s) — e.g.
      Rockerz earbuds vs. Xtend smartwatches — vs. brand-wide
- [ ] Each member scrapes one source in parallel (Play Store / e-commerce /
      social) to speed up data collection
- [ ] Target volume: aim for 1,000+ reviews per source if possible for
      meaningful topic modeling
- [ ] Decide LDA vs. BERTopic for final deliverable based on runtime and
      topic quality on real data
- [ ] Write the summary report interpreting findings + management
      recommendations (deliverable #3)
