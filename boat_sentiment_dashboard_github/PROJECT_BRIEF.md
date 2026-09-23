# Project Brief: boAt Sentiment & Theme Intelligence System

Context for an AI coding agent picking up this project inside Antigravity.
This consolidates everything decided and built so far so you don't need
the original chat history.

## 1. Course context

- Course: Artificial Intelligence for Business, PGP-BL Batch 06, IIM Kozhikode
- Team: Rohan Narayan Kharade, Ujjwal Prakash, Vedanshu Seedwan, Yunus
  Shaikh, Aishwarya Jadhav
- Deliverables required: working NLP pipeline (code), an interactive
  decision-support dashboard, a summary report interpreting findings
- Course modules the project must visibly map to: Machine Learning,
  Deep Learning, NLP, Generative AI, Business Roadmap with AI — the
  architecture below was deliberately designed so each module has a
  distinct, identifiable stage in the pipeline.

## 2. Project decision

**Brand chosen: boAt** (Indian audio/wearables brand), because it has all
three review source types needed:
- Google Play Store (their app)
- E-commerce (Amazon.in / Flipkart product reviews — richest source)
- Social (Reddit / Twitter complaints and mentions)

## 3. Architecture (what maps to which course module)

| Layer | Technique | Course module | File |
|---|---|---|---|
| Data ingestion | Scraping (Play Store, Amazon/Flipkart, Reddit/Twitter) | Business Transformation with AI | `scrapers/*.py` |
| Preprocessing | NLTK, regex, tokenization | NLP in Business | `pipeline/preprocessing.py` |
| Sentiment | VADER (lexicon) + DistilBERT transformer (optional) | Machine Learning + Deep Learning | `pipeline/sentiment_analysis.py` |
| Theme extraction | LDA (default) + BERTopic (optional upgrade) | Deep Learning + NLP | `pipeline/topic_modeling.py` |
| Insight synthesis | LLM (Claude or Gemini) executive summary | Generative AI for Business | `pipeline/insight_agent.py` |
| Decision support | Streamlit + Plotly dashboard | Business Roadmap with AI | `dashboard/app.py` |
| Orchestration | Fault-isolated pipeline runner | — | `orchestrator.py` |

Full system flow:
```
Raw feedback (Play Store / Amazon / Flipkart / Reddit / Twitter)
  -> Scraping layer (per-source, isolated failures)
  -> Preprocessing (clean, tokenize, normalize)
  -> Sentiment engine (VADER + optional transformer)
  -> Theme extraction (LDA + optional BERTopic)          [runs in parallel with sentiment]
  -> Structured insight layer (sentiment x theme matrix)
  -> GenAI insight agent (LLM executive summary)
  -> Decision-support dashboard (Streamlit, localhost:8501)
  -> Business stakeholder action
```

## 4. What's built and already tested

Everything below has been tested end-to-end in a sandboxed environment
(minus live scraping and live LLM API calls, which need real internet —
see "Not yet tested" section).

- **`pipeline/preprocessing.py`** — merges multiple source CSVs into one
  schema (`review_text, rating, date, source`), dedupes, produces both a
  lightly-cleaned column (for sentiment) and a heavily-cleaned column
  (for topic modeling).
- **`pipeline/sentiment_analysis.py`** — VADER by default
  (`score_with_vader`), optional HuggingFace transformer
  (`score_with_transformer`, needs `transformers`+`torch`). Entry point:
  `add_sentiment(df, method="vader"|"transformer")`.
- **`pipeline/topic_modeling.py`** — LDA via scikit-learn by default
  (`run_lda`, tunable `min_df`/`max_df`/`n_topics`), optional BERTopic
  (`run_bertopic`, needs `bertopic`+`sentence-transformers`).
- **`pipeline/insight_agent.py`** — builds a compact JSON stats payload
  (never sends raw review text at scale to the LLM) and prompts
  Claude or Gemini for a ~250-word executive summary (sentiment health,
  top 3 themes, most urgent issue, 2 recommended actions). Falls back to
  a deterministic rule-based summary if no API key is set — pipeline
  never crashes without a key, but a real key is needed for genuine
  GenAI output before final submission.
- **`orchestrator.py`** — runs the full pipeline as one command.
  Each scraper source is isolated (one failing doesn't kill the run).
  Modes: `--dry-run` (reuse existing `data/*.csv`, no scraping),
  `--sources playstore amazon reddit` (live scrape), `--schedule
  hourly|daily` (loops forever). Logs to `logs/orchestrator.log`.
  Writes timestamped output plus fixed `_latest` files
  (`outputs/processed_reviews_latest.csv`,
  `outputs/executive_summary_latest.txt`) that the dashboard always reads.
- **`dashboard/app.py`** — Streamlit app. Auto-detects and loads the
  latest orchestrator run (falls back to bundled sample data if no run
  has happened yet). Shows: AI executive summary, KPIs, sentiment
  distribution pie + by-source bar, theme frequency, sentiment-within-
  theme, sentiment trend over time, flagged most-negative reviews table,
  raw data explorer. Boot-tested headlessly — starts cleanly on port 8501.
- **`start_local.sh` / `start_local.bat`** — one-command launcher: runs
  the pipeline (dry-run by default, `--live` for real scraping, `--watch`
  for hourly background refresh) then launches the dashboard.
- **`scrapers/*.py`** — `playstore_scraper.py` (google-play-scraper,
  no auth needed), `ecommerce_scraper.py` (Selenium, Amazon.in, selectors
  will likely need fixing since Amazon changes HTML often — has a
  documented Kaggle-dataset fallback plan), `social_scraper.py` (PRAW for
  Reddit, snscrape for Twitter/X — Twitter scraping is unreliable since X
  locked down its platform, documented as a known risk).
- **`data/sample_reviews.csv`** — 30 hand-written realistic boAt-style
  reviews used to validate the whole pipeline works before real data
  exists.
- **`.github/workflows/run_pipeline.yml`** — optional GitHub Actions
  workflow (daily cron + push trigger), NOT the primary way to run this;
  local-first via `start_local.sh` is the intended workflow.
- **`.env.example`** — template for `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`
  / Reddit API credentials.

## 5. Not yet tested (needs real environment / real internet)

- Live scraping against Play Store, Amazon, Flipkart, Reddit, Twitter —
  sandbox network was restricted to package registries only.
- Real Claude/Gemini API calls from `insight_agent.py` — only the
  no-API-key fallback path was verified.
- Browser rendering of the Streamlit dashboard (only headless boot was
  verified, not visual/interactive behavior).
- Amazon/Flipkart CSS selectors in `ecommerce_scraper.py` — flagged as
  likely to need fixing since these sites change HTML frequently.

## 6. How to run it (inside Antigravity)

```bash
# 1. Open the extracted project folder as the workspace root in Antigravity
# 2. In the integrated terminal:
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in ANTHROPIC_API_KEY (or GOOGLE_API_KEY)
chmod +x start_local.sh            # Mac/Linux only

# 3. Sanity-check the pipeline alone before involving the dashboard:
python orchestrator.py --dry-run

# 4. Full run + dashboard:
./start_local.sh          # dry-run with sample data, then opens http://localhost:8501
./start_local.sh --live   # scrapes playstore+amazon+reddit for real, then dashboard
./start_local.sh --watch  # also re-runs the pipeline hourly in the background
```

Windows: use `start_local.bat` instead of `start_local.sh`.

## 7. Immediate next steps / open items

- [ ] Verify live scraping actually works against current Play Store /
      Amazon / Flipkart / Reddit — fix Selenium selectors if broken
- [ ] Get a real `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY` into `.env` and
      confirm the GenAI executive summary generates properly (not the
      rule-based fallback)
- [ ] Decide final product scope within boAt (brand-wide vs. one product
      line, e.g. Rockerz earbuds vs. Xtend smartwatches)
- [ ] Split scraping work across the 5 team members (one source each) to
      parallelize data collection — target 1,000+ reviews per source
- [ ] Once real data volume exists, re-tune `min_df`/`n_topics` in
      `run_lda` (current defaults assume thousands of reviews; sample
      testing used `min_df=2` for only 30 rows)
- [ ] Decide LDA vs. BERTopic for the final deliverable based on topic
      quality/runtime on real data
- [ ] Write the summary report interpreting findings + management
      recommendations (deliverable #3 for the course)
- [ ] Build the session-by-session timeline (course proposal section 8)
      mapping project phases to weeks in the syllabus — not yet done
- [ ] Not yet built: in-dashboard "refresh now" button (currently only
      via `--watch` background loop); alerting when negative sentiment spikes
