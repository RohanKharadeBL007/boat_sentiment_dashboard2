"""
Scrapes reviews for ALL boAt apps from the Google Play Store.

Apps scraped:
  - boAt Shopping    (com.coffye.khjenr)
  - boAt Wearables   (com.boAt.wristgear)
  - boAt Hearables   (com.boAt.hearables)
  - boAt Crest       (com.coveiot.android.boat)
  - boAt Wave        (com.boat.Xtend.two)

Usage:
    python playstore_scraper.py
    python playstore_scraper.py --app_id com.boAt.hearables   # single app

Saves: ../data/playstore_reviews.csv  (all apps combined)
"""

import argparse
import os
import sys

import pandas as pd
from google_play_scraper import Sort, reviews_all

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from products_config import BOAT_ALL_APP_IDS

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "playstore_reviews.csv")


def scrape_single_app(app_id: str, app_name: str) -> pd.DataFrame:
    print(f"[Play Store] Fetching reviews for: {app_name} ({app_id}) ...")
    try:
        raw_reviews = reviews_all(
            app_id,
            sleep_milliseconds=200,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
        )
    except Exception as e:
        print(f"[Play Store] ERROR for {app_name}: {e}")
        return pd.DataFrame()

    if not raw_reviews:
        print(f"[Play Store] No reviews for {app_name}.")
        return pd.DataFrame()

    df = pd.DataFrame(raw_reviews)
    keep_cols = ["reviewId", "userName", "content", "score", "thumbsUpCount", "at"]
    df = df[[c for c in keep_cols if c in df.columns]]
    df = df.rename(columns={
        "content": "review_text",
        "score": "rating",
        "at": "date",
    })
    df["source"] = "play_store"
    df["product"] = app_name
    print(f"[Play Store] {app_name}: {len(df)} reviews")
    return df


def scrape_all_apps() -> pd.DataFrame:
    all_dfs = []
    for app_id, app_name in BOAT_ALL_APP_IDS:
        df = scrape_single_app(app_id, app_name)
        if not df.empty:
            all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape boAt Play Store reviews")
    parser.add_argument("--app_id", default=None,
                        help="Scrape a single app by ID (default: all boAt apps)")
    parser.add_argument("--app_name", default="custom")
    parser.add_argument("--out", default=OUTPUT_PATH)
    args = parser.parse_args()

    if args.app_id:
        df = scrape_single_app(args.app_id, args.app_name)
    else:
        df = scrape_all_apps()

    if not df.empty:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"\n[Play Store] Saved {len(df)} total reviews -> {args.out}")
    else:
        print("\n[Play Store] No reviews saved.")
