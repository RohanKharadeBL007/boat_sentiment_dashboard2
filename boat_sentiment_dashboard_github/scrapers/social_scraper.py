"""
Scrapes social mentions of boAt from Reddit (PRAW) and Twitter/X (snscrape).
Loops over all products configured in products_config.py.

REDDIT SETUP (one-time):
    1. Go to https://www.reddit.com/prefs/apps
    2. Click "Create app" -> choose "script" type
    3. Name: boat-sentiment, Redirect URI: http://localhost:8080
    4. Copy the client_id (under the app name) and client_secret
    5. Set them in your .env file as REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET

TWITTER/X:
    snscrape works without API keys but X has increasingly blocked it.
    If Twitter scraping fails, the script will log it and continue with Reddit data.

Usage:
    python social_scraper.py
    python social_scraper.py --product rockerz   # one product only
    python social_scraper.py --limit 200         # fewer posts per product

Saves:
    ../data/reddit_mentions.csv
    ../data/twitter_mentions.csv  (if Twitter scraping works)
"""

import argparse
import json
import os
import subprocess
import sys

import pandas as pd
import praw
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from products_config import PRODUCTS

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "boat-sentiment-project by u/your_reddit_username")

REDDIT_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "reddit_mentions.csv")
TWITTER_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "twitter_mentions.csv")


# --------------------------------------------------------------------------- #
# Reddit
# --------------------------------------------------------------------------- #

def scrape_reddit_for_product(reddit: praw.Reddit, query: str, product_name: str,
                               limit: int = 500) -> list[dict]:
    """Fetch posts + top comments matching a query for one product."""
    records = []
    print(f"[Reddit] Searching: '{query}' (limit={limit}) ...")

    try:
        submissions = list(reddit.subreddit("all").search(query, limit=limit, sort="new"))
    except Exception as e:
        print(f"[Reddit] ERROR searching for '{query}': {e}")
        return records

    for submission in submissions:
        records.append({
            "review_text": (submission.title + " " + (submission.selftext or "")).strip(),
            "rating": None,
            "date": pd.to_datetime(submission.created_utc, unit="s"),
            "source": "reddit",
            "product": product_name,
            "upvotes": submission.score,
            "url": submission.url,
        })

        # Top 10 comments per post
        try:
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:10]:
                if comment.body and comment.body != "[deleted]":
                    records.append({
                        "review_text": comment.body,
                        "rating": None,
                        "date": pd.to_datetime(comment.created_utc, unit="s"),
                        "source": "reddit_comment",
                        "product": product_name,
                        "upvotes": comment.score,
                        "url": f"https://reddit.com{comment.permalink}",
                    })
        except Exception:
            pass

    print(f"[Reddit] '{product_name}': {len(records)} posts+comments")
    return records


def scrape_reddit_all(limit_per_product: int = 500, product_key: str = None) -> pd.DataFrame:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        print("[Reddit] REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set in .env — skipping.")
        return pd.DataFrame()

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

    all_records = []
    products_to_scrape = {product_key: PRODUCTS[product_key]} if product_key else PRODUCTS

    for key, cfg in products_to_scrape.items():
        records = scrape_reddit_for_product(
            reddit, cfg["reddit_query"], cfg["name"], limit=limit_per_product
        )
        all_records.extend(records)

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Twitter / X  (via snscrape — may be unreliable)
# --------------------------------------------------------------------------- #

def scrape_twitter_for_product(query: str, product_name: str,
                                max_tweets: int = 500) -> list[dict]:
    cmd = [
        "snscrape", "--jsonl", "--max-results", str(max_tweets),
        "twitter-search", query,
    ]
    print(f"[Twitter] Searching: '{query}' (max={max_tweets}) ...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        print("[Twitter] snscrape not found on PATH. Skipping Twitter.")
        return []
    except subprocess.TimeoutExpired:
        print("[Twitter] snscrape timed out. Skipping Twitter.")
        return []

    records = []
    for line in result.stdout.splitlines():
        try:
            tweet = json.loads(line)
            text = tweet.get("rawContent") or tweet.get("content", "")
            if text:
                records.append({
                    "review_text": text,
                    "rating": None,
                    "date": tweet.get("date"),
                    "source": "twitter",
                    "product": product_name,
                    "likes": tweet.get("likeCount"),
                })
        except json.JSONDecodeError:
            continue

    print(f"[Twitter] '{product_name}': {len(records)} tweets")
    return records


def scrape_twitter_all(max_per_product: int = 500, product_key: str = None) -> pd.DataFrame:
    all_records = []
    products_to_scrape = {product_key: PRODUCTS[product_key]} if product_key else PRODUCTS

    for key, cfg in products_to_scrape.items():
        query = cfg["reddit_query"].replace("OR", "OR") + " lang:en"
        records = scrape_twitter_for_product(query, cfg["name"], max_tweets=max_per_product)
        all_records.extend(records)

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Instagram (via instaloader)
# --------------------------------------------------------------------------- #

def scrape_instagram_for_product(query: str, product_name: str, max_posts: int = 50) -> list[dict]:
    import instaloader
    
    print(f"[Instagram] Searching: '{query}' (max_posts={max_posts}) ...")
    records = []
    
    L = instaloader.Instaloader(quiet=True)
    try:
        # Search for posts with a hashtag based on the product name, e.g., #boatrockerz
        hashtag = query.split()[0].replace(" ", "").replace("boAt", "boat").lower()
        if not hashtag.startswith("#"):
            hashtag = f"boat{hashtag}" # e.g. boatairdopes
            
        posts = instaloader.Hashtag.from_name(L.context, hashtag).get_posts()
        
        count = 0
        for post in posts:
            if count >= max_posts:
                break
                
            text = post.caption or ""
            if text:
                records.append({
                    "review_text": text,
                    "rating": None,
                    "date": post.date,
                    "source": "instagram",
                    "product": product_name,
                    "likes": post.likes,
                })
            count += 1
            
    except Exception as e:
        print(f"[Instagram] ERROR scraping hashtag '{hashtag}': {e}")
        
    print(f"[Instagram] '{product_name}': {len(records)} posts")
    return records


def scrape_instagram_all(max_per_product: int = 50, product_key: str = None) -> pd.DataFrame:
    all_records = []
    products_to_scrape = {product_key: PRODUCTS[product_key]} if product_key else PRODUCTS

    for key, cfg in products_to_scrape.items():
        records = scrape_instagram_for_product(cfg["name"], cfg["name"], max_posts=max_per_product)
        all_records.extend(records)

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Twitter and Instagram for boAt mentions")
    parser.add_argument("--limit", type=int, default=100,
                        help="Posts to fetch per product per platform (default: 100)")
    parser.add_argument("--product", default=None, choices=list(PRODUCTS.keys()),
                        help="Scrape only this product (default: all)")
    parser.add_argument("--skip_twitter", action="store_true", help="Skip Twitter")
    parser.add_argument("--skip_instagram", action="store_true", help="Skip Instagram")
    args = parser.parse_args()

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    INSTAGRAM_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "instagram_mentions.csv")

    # Twitter
    if not args.skip_twitter:
        try:
            twitter_df = scrape_twitter_all(max_per_product=args.limit, product_key=args.product)
            if not twitter_df.empty:
                twitter_df.to_csv(TWITTER_OUT, index=False)
                print(f"[Twitter] Saved {len(twitter_df)} records -> {TWITTER_OUT}")
            else:
                print("[Twitter] No tweets scraped.")
        except Exception as e:
            print(f"[Twitter] Failed: {e}.")
    else:
        print("[Twitter] Skipped.")
        
    # Instagram
    if not args.skip_instagram:
        try:
            instagram_df = scrape_instagram_all(max_per_product=args.limit, product_key=args.product)
            if not instagram_df.empty:
                instagram_df.to_csv(INSTAGRAM_OUT, index=False)
                print(f"[Instagram] Saved {len(instagram_df)} records -> {INSTAGRAM_OUT}")
            else:
                print("[Instagram] No posts scraped.")
        except Exception as e:
            print(f"[Instagram] Failed: {e}.")
    else:
        print("[Instagram] Skipped.")

    print("\nDone! Next step: python run_pipeline.py")
