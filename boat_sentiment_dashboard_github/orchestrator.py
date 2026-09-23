"""
Master orchestrator -- runs the ENTIRE system automatically, end to end:

  scrape -> merge -> preprocess -> sentiment -> topics -> GenAI insight
  -> write processed CSV + executive summary -> (optionally) push to dashboard

Designed to run unattended: via cron, GitHub Actions, or a simple
`python orchestrator.py` on a schedule. Every stage is wrapped so a
failure in one source (e.g. Twitter scraping blocked) does not kill the
whole run -- it logs and continues with whatever data is available.

Usage:
    python orchestrator.py                      # run once, all sources
    python orchestrator.py --sources playstore reddit
    python orchestrator.py --schedule daily      # loop forever, run once/day
    python orchestrator.py --dry-run             # skip scraping, use existing data/*.csv
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.preprocessing import load_and_merge, preprocess_dataframe
from pipeline.sentiment_analysis import add_sentiment
from pipeline.topic_modeling import run_lda
from pipeline.insight_agent import generate_executive_summary

LOG_DIR = Path("logs")
DATA_DIR = Path("data")
OUTPUT_DIR = Path("outputs")
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "orchestrator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("orchestrator")


# --------------------------------------------------------------------------
# Stage 1: Scraping (each source isolated -- one failing doesn't kill the run)
# --------------------------------------------------------------------------

def run_scrapers(sources: list[str]) -> list[str]:
    """Runs requested scrapers as subprocesses, returns list of CSV paths
    successfully produced. Scraper failures are logged and skipped."""
    produced = []
    
    # Map sources to the script that produces them and the expected output file
    source_to_script = {
        "playstore": ("scrapers/playstore_scraper.py", DATA_DIR / "playstore_reviews.csv"),
        "amazon": ("scrapers/ecommerce_scraper.py", DATA_DIR / "amazon_reviews.csv"),
        "flipkart": ("scrapers/ecommerce_scraper.py", DATA_DIR / "flipkart_reviews.csv"),
        "website": ("scrapers/website_scraper.py", DATA_DIR / "website_reviews.csv"),
        "twitter": ("scrapers/social_scraper.py", DATA_DIR / "twitter_mentions.csv"),
        "instagram": ("scrapers/social_scraper.py", DATA_DIR / "instagram_mentions.csv"),
        "reddit": ("scrapers/social_scraper.py", DATA_DIR / "reddit_mentions.csv"),
    }

    import subprocess
    
    scripts_to_run = {}
    for source in sources:
        if source not in source_to_script:
            log.warning(f"Unknown source '{source}', skipping.")
            continue
        script, expected_output = source_to_script[source]
        if script not in scripts_to_run:
            scripts_to_run[script] = []
        scripts_to_run[script].append((source, expected_output))

    for script, expected_outputs in scripts_to_run.items():
        log.info(f"Running scraper script: {script}")
        try:
            result = subprocess.run(
                [sys.executable, script], capture_output=True, text=True, timeout=1800
            )
            if result.returncode != 0:
                log.error(f"Scraper script {script} failed:\n{result.stderr[-2000:]}")
                continue
                
            for source, expected_output in expected_outputs:
                if expected_output.exists():
                    produced.append(str(expected_output))
                    log.info(f"Source {source} OK -> {expected_output}")
                else:
                    log.warning(f"Source {source} missing expected output: {expected_output}")
                    
        except subprocess.TimeoutExpired:
            log.error(f"Scraper script {script} timed out after 30 minutes, skipping.")
        except Exception as e:
            log.error(f"Scraper script {script} raised an exception: {e}\n{traceback.format_exc()}")

    return produced


def discover_existing_data() -> list[str]:
    """Used in --dry-run mode: picks up whatever CSVs already exist in data/."""
    existing = [str(p) for p in DATA_DIR.glob("*.csv")]
    if not existing:
        # fall back to the bundled sample so the pipeline still runs
        sample = DATA_DIR / "sample_reviews.csv"
        if sample.exists():
            existing = [str(sample)]
    return existing


# --------------------------------------------------------------------------
# Stage 2-4: ML/DL/NLP pipeline
# --------------------------------------------------------------------------

def run_analysis_pipeline(csv_paths: list[str], n_topics: int, min_df: int,
                           sentiment_method: str):
    log.info(f"Merging {len(csv_paths)} source file(s)...")
    df = load_and_merge(csv_paths)
    log.info(f"  {len(df)} reviews after merge/dedup")

    log.info("Preprocessing...")
    df = preprocess_dataframe(df)
    log.info(f"  {len(df)} reviews after cleaning")

    if len(df) < 10:
        raise RuntimeError(f"Only {len(df)} reviews after cleaning -- too little data to proceed.")

    log.info(f"Scoring sentiment ({sentiment_method})...")
    df = add_sentiment(df, method=sentiment_method)
    log.info(f"  {df['sentiment_label'].value_counts().to_dict()}")

    log.info(f"Extracting {n_topics} topics...")
    topic_keywords, df = run_lda(df, n_topics=n_topics, min_df=min_df)
    for idx, words in topic_keywords.items():
        log.info(f"  Topic {idx}: {', '.join(words)}")

    return df, topic_keywords


# --------------------------------------------------------------------------
# Stage 5: GenAI insight layer
# --------------------------------------------------------------------------

def run_insight_agent(df, backend: str) -> str:
    log.info(f"Generating executive summary via {backend}...")
    try:
        summary = generate_executive_summary(df, backend=backend)
        log.info("Executive summary generated.")
        return summary
    except Exception as e:
        log.error(f"Insight agent failed: {e}\n{traceback.format_exc()}")
        return "Executive summary generation failed -- see logs/orchestrator.log"


# --------------------------------------------------------------------------
# Full run
# --------------------------------------------------------------------------

def run_once(sources: list[str], n_topics: int, min_df: int,
             sentiment_method: str, insight_backend: str, dry_run: bool):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log.info(f"=== Orchestrator run {run_id} starting ===")

    if dry_run:
        log.info("Dry run: skipping scrapers, using existing data/*.csv")
        csv_paths = discover_existing_data()
    else:
        csv_paths = run_scrapers(sources)
        if not csv_paths:
            log.warning("No scrapers succeeded, falling back to existing data on disk.")
            csv_paths = discover_existing_data()

    if not csv_paths:
        log.error("No data available from scrapers or disk. Aborting run.")
        return None

    try:
        df, topic_keywords = run_analysis_pipeline(csv_paths, n_topics, min_df, sentiment_method)
    except Exception as e:
        log.error(f"Analysis pipeline failed: {e}\n{traceback.format_exc()}")
        return None

    summary_text = run_insight_agent(df, insight_backend)

    processed_path = OUTPUT_DIR / f"processed_reviews_{run_id}.csv"
    latest_path = OUTPUT_DIR / "processed_reviews_latest.csv"
    df.to_csv(processed_path, index=False)
    df.to_csv(latest_path, index=False)  # dashboard always reads this fixed filename

    summary_path = OUTPUT_DIR / f"executive_summary_{run_id}.txt"
    latest_summary_path = OUTPUT_DIR / "executive_summary_latest.txt"
    summary_path.write_text(summary_text)
    latest_summary_path.write_text(summary_text)

    log.info(f"Run {run_id} complete. {len(df)} reviews processed.")
    log.info(f"  -> {processed_path}")
    log.info(f"  -> {summary_path}")
    log.info("=== Run finished ===\n")

    return {
        "run_id": run_id,
        "n_reviews": len(df),
        "processed_path": str(processed_path),
        "summary_path": str(summary_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Run the boAt sentiment system automatically.")
    parser.add_argument("--sources", nargs="+", default=["playstore", "amazon", "flipkart", "website", "twitter", "instagram"])
    parser.add_argument("--n_topics", type=int, default=6)
    parser.add_argument("--min_df", type=int, default=5)
    parser.add_argument("--sentiment_method", default="vader", choices=["vader", "transformer"])
    parser.add_argument("--insight_backend", default="gemini", choices=["claude", "gemini"])
    parser.add_argument("--dry-run", action="store_true",
                         help="Skip scraping, use whatever CSVs already exist in data/")
    parser.add_argument("--schedule", choices=["once", "hourly", "daily"], default="once")
    args = parser.parse_args()

    interval_seconds = {"once": None, "hourly": 3600, "daily": 86400}[args.schedule]

    if interval_seconds is None:
        run_once(args.sources, args.n_topics, args.min_df,
                  args.sentiment_method, args.insight_backend, args.dry_run)
    else:
        log.info(f"Running on a {args.schedule} schedule. Ctrl+C to stop.")
        while True:
            run_once(args.sources, args.n_topics, args.min_df,
                      args.sentiment_method, args.insight_backend, args.dry_run)
            log.info(f"Sleeping {interval_seconds}s until next run...")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
