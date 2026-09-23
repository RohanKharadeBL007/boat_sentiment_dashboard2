"""
Scrapes reviews from boAt's official website (boat-lifestyle.com).
Uses Shopify/Judge.me API endpoints if available, or BeautifulSoup for scraping HTML.

USAGE:
    python website_scraper.py --pages 5

Saves: 
    ../data/website_reviews.csv
"""

import argparse
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from products_config import PRODUCTS

WEBSITE_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "website_reviews.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def scrape_website_product(product_url: str, product_name: str, max_pages: int = 5) -> list[dict]:
    if "PASTE" in product_url or not product_url.startswith("http"):
        print(f"[Website] Skipping '{product_name}' — valid URL not provided.")
        return []

    print(f"\n[Website] Scraping: {product_name}")
    records = []
    
    # Normally boAt uses Okendo or Judge.me for reviews.
    # Without knowing the exact API payload for the boAt website, we'll try a generic HTML scrape.
    # If this fails, the user will need to provide the actual API endpoint for Okendo/Judge.me
    
    for page in range(1, max_pages + 1):
        url = f"{product_url}?page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"[Website] Page {page}: Request failed (status code: {response.status_code})")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # This is a generic guess for Shopify review blocks.
            # Real boAt website uses Okendo, which loads via JS API.
            review_blocks = soup.find_all("div", class_="review-item") 
            
            if not review_blocks:
                print(f"[Website] Page {page}: No HTML review blocks found. (The site likely loads reviews via JavaScript/API)")
                break

            for block in review_blocks:
                body = block.find("div", class_="review-content")
                body = body.text.strip() if body else ""
                
                title = block.find("div", class_="review-title")
                title = title.text.strip() if title else ""
                
                rating = block.find("span", class_="jdgm-rev__rating") # Judge.me example
                rating = float(rating["data-score"]) if rating and "data-score" in rating.attrs else None
                
                date = block.find("span", class_="review-date")
                date = date.text.strip() if date else ""
                
                if body:
                    records.append({
                        "review_text": body,
                        "review_title": title,
                        "rating": rating,
                        "date": date,
                        "source": "boat_website",
                        "product": product_name,
                    })

            print(f"[Website] {product_name} — Page {page}: found {len(review_blocks)} reviews.")
            time.sleep(2)
        except Exception as e:
            print(f"[Website] Error scraping page {page}: {e}")
            break

    return records


def scrape_website_all(max_pages: int = 5):
    all_records = []

    for key, cfg in PRODUCTS.items():
        records = scrape_website_product(cfg.get("website_url", ""), cfg["name"], max_pages)
        if records:
            all_records.extend(records)

    df = pd.DataFrame(all_records)
    if not df.empty:
        os.makedirs(os.path.dirname(WEBSITE_OUTPUT), exist_ok=True)
        df.to_csv(WEBSITE_OUTPUT, index=False)
        print(f"\n[Website] Saved {len(df)} total reviews -> {WEBSITE_OUTPUT}")
    else:
        print("\n[Website] No reviews scraped. (Note: boAt website reviews likely require calling the Okendo/Judge.me API directly).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape boAt official website reviews")
    parser.add_argument("--pages", type=int, default=5, help="Max pages per product")
    args = parser.parse_args()

    scrape_website_all(max_pages=args.pages)
