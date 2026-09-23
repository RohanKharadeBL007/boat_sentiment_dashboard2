"""
Scrapes Amazon.in and Flipkart reviews for all boAt products defined in products_config.py.
This script uses `requests` and `BeautifulSoup` instead of Selenium to avoid driver issues.

USAGE:
    python ecommerce_scraper.py --pages 10

Saves: 
    ../data/amazon_reviews.csv
    ../data/flipkart_reviews.csv
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

AMAZON_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "amazon_reviews.csv")
FLIPKART_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "flipkart_reviews.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}


def scrape_amazon_product(product_url: str, product_name: str, max_pages: int = 5) -> list[dict]:
    if "PASTE" in product_url or not product_url.startswith("http"):
        print(f"[Amazon] Skipping '{product_name}' — valid URL not provided.")
        return []

    print(f"\n[Amazon] Scraping: {product_name}")
    records = []

    for page in range(1, max_pages + 1):
        url = f"{product_url}&pageNumber={page}" if "?" in product_url else f"{product_url}?pageNumber={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"[Amazon] Page {page}: Request failed (status code: {response.status_code})")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            review_blocks = soup.find_all("div", {"data-hook": "review"})
            
            if not review_blocks:
                print(f"[Amazon] Page {page}: No review blocks found. (Anti-bot might have triggered)")
                break

            for block in review_blocks:
                # Rating
                rating_elem = block.find("i", {"data-hook": "review-star-rating"})
                if not rating_elem:
                    rating_elem = block.find("i", {"data-hook": "cmps-review-star-rating"})
                rating = None
                if rating_elem and rating_elem.text:
                    try:
                        rating = float(rating_elem.text.split(" ")[0].replace(",", "."))
                    except Exception:
                        pass
                
                # Title
                title_elem = block.find("a", {"data-hook": "review-title"})
                title = title_elem.text.strip() if title_elem else ""
                if title and "\n" in title:
                    title = title.split("\n")[-1].strip() # Sometimes title has rating embedded
                
                # Date
                date_elem = block.find("span", {"data-hook": "review-date"})
                date = date_elem.text.strip() if date_elem else ""

                # Body
                body_elem = block.find("span", {"data-hook": "review-body"})
                body = body_elem.text.strip() if body_elem else ""
                
                if body:
                    records.append({
                        "review_text": body,
                        "review_title": title,
                        "rating": rating,
                        "date": date,
                        "source": "amazon",
                        "product": product_name,
                    })
            
            print(f"[Amazon] {product_name} — Page {page}: found {len(review_blocks)} reviews.")
            time.sleep(2)  # Polite delay
        except Exception as e:
            print(f"[Amazon] Error scraping page {page}: {e}")
            break

    return records


def scrape_flipkart_product(product_url: str, product_name: str, max_pages: int = 5) -> list[dict]:
    if "PASTE" in product_url or not product_url.startswith("http"):
        print(f"[Flipkart] Skipping '{product_name}' — valid URL not provided.")
        return []

    print(f"\n[Flipkart] Scraping: {product_name}")
    records = []
    
    for page in range(1, max_pages + 1):
        url = f"{product_url}&page={page}" if "?" in product_url else f"{product_url}?page={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"[Flipkart] Page {page}: Request failed (status code: {response.status_code})")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            # Flipkart review blocks usually have specific class patterns like '_27M-vq'
            review_blocks = soup.find_all("div", class_="_27M-vq")
            
            if not review_blocks:
                print(f"[Flipkart] Page {page}: No review blocks found. (Anti-bot might have triggered)")
                break

            for block in review_blocks:
                # Rating
                rating_elem = block.find("div", class_="_3LWZlK")
                rating = float(rating_elem.text.strip()) if rating_elem and rating_elem.text else None
                
                # Title
                title_elem = block.find("p", class_="_2-N8zT")
                title = title_elem.text.strip() if title_elem else ""
                
                # Body
                body_elem = block.find("div", class_="t-ZTKy")
                body = body_elem.text.strip() if body_elem else ""
                
                # Date (Flipkart dates are often relative like '1 month ago', but sometimes absolute)
                date_elem = block.find_all("p", class_="_2sc7ZR")
                date = date_elem[-1].text.strip() if date_elem else ""
                
                if body:
                    records.append({
                        "review_text": body,
                        "review_title": title,
                        "rating": rating,
                        "date": date,
                        "source": "flipkart",
                        "product": product_name,
                    })

            print(f"[Flipkart] {product_name} — Page {page}: found {len(review_blocks)} reviews.")
            time.sleep(2)
        except Exception as e:
            print(f"[Flipkart] Error scraping page {page}: {e}")
            break

    return records


def scrape_ecommerce_all(max_pages: int = 5):
    amazon_all = []
    flipkart_all = []

    for key, cfg in PRODUCTS.items():
        # Amazon
        amz_records = scrape_amazon_product(cfg.get("amazon_url", ""), cfg["name"], max_pages)
        if amz_records:
            amazon_all.extend(amz_records)
            
        # Flipkart
        fk_records = scrape_flipkart_product(cfg.get("flipkart_url", ""), cfg["name"], max_pages)
        if fk_records:
            flipkart_all.extend(fk_records)

    # Save Amazon
    amz_df = pd.DataFrame(amazon_all)
    if not amz_df.empty:
        os.makedirs(os.path.dirname(AMAZON_OUTPUT), exist_ok=True)
        amz_df.to_csv(AMAZON_OUTPUT, index=False)
        print(f"\n[Amazon] Saved {len(amz_df)} total reviews -> {AMAZON_OUTPUT}")
    else:
        print("\n[Amazon] No reviews scraped.")

    # Save Flipkart
    fk_df = pd.DataFrame(flipkart_all)
    if not fk_df.empty:
        os.makedirs(os.path.dirname(FLIPKART_OUTPUT), exist_ok=True)
        fk_df.to_csv(FLIPKART_OUTPUT, index=False)
        print(f"[Flipkart] Saved {len(fk_df)} total reviews -> {FLIPKART_OUTPUT}")
    else:
        print("[Flipkart] No reviews scraped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Amazon and Flipkart reviews")
    parser.add_argument("--pages", type=int, default=5, help="Max pages per product")
    args = parser.parse_args()

    scrape_ecommerce_all(max_pages=args.pages)
