"""
Central product configuration for the boAt Sentiment Dashboard.

HOW TO ADD A NEW PRODUCT:
    1. Add an entry to PRODUCTS dict below with a unique key.
    2. Fill in the product name, Amazon review URL, Play Store app ID,
       and Reddit search query for that product.
    3. Re-run scrapers / orchestrator — they pick up the new product automatically.

HOW TO FIND THE AMAZON REVIEW URL:
    - Go to amazon.in
    - Search for the product -> open product page -> click "See all reviews"
    - Copy the URL from the address bar. It looks like:
      https://www.amazon.in/product-reviews/B0XXXXXXXX/?reviewerType=all_reviews
    - Paste that URL as the value for "amazon_url" below.
"""

PRODUCTS = {
    # ------------------------------------------------------------------ #
    # Product 1: boAt Rockerz (earphones / headphones)
    # ------------------------------------------------------------------ #
    "rockerz": {
        "name": "boAt Rockerz",
        "amazon_url": "https://www.amazon.in/portal/customer-reviews/B0FG2QDFD7/ref=cm_cr_dp_d_show_all_top?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews",
        "flipkart_url": "https://www.flipkart.com/boat-rockerz-425-25h-battery-beast-mode-enx-dual-pair-stream-ad-free-music-via-app-bluetooth/product-reviews/itm43f9698b709bf?pid=ACCH44DVGNJ3DHFX&lid=LSTACCH44DVGNJ3DHFXEANEVM&marketplace=FLIPKART",
        "website_url": "https://www.boat-lifestyle.com/products/boat-rockerz-412-wireless-headphones",
        "playstore_app_id": None,
        "reddit_query": "boAt Rockerz earphones OR headphones",
    },

    # ------------------------------------------------------------------ #
    # Product 2: boAt Airdopes (TWS earbuds)
    # ------------------------------------------------------------------ #
    "airdopes": {
        "name": "boAt Airdopes",
        "amazon_url": "https://www.amazon.in/portal/customer-reviews/B0GZMYZW7R/ref=cm_cr_dp_d_show_all_top?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews",
        "flipkart_url": "https://www.flipkart.com/boat-airdopes-141-gen-2-4-mics-enx-tech-48h-battery-asap-charge-low-latency-bt-v5-4-bluetooth/p/itm97186a453279a?pid=ACCHGG7ND9BRXRGZ&lid=LSTACCHGG7ND9BRXRGZF63SSL&marketplace=FLIPKART&q=boAt+Airdopes+%28TWS+earbuds%29&store=0pm%2Ffcn%2F821&srno=s_1_1&otracker=search&otracker1=search&fm=Search&iid=1258f014-3997-467b-b05d-bfffa7cb20a7.ACCHGG7ND9BRXRGZ.SEARCH&ppt=sp&ppn=sp&ssid=ly5zfsdh340000001790075979862&qH=ed167ab9cdc30b10&ov_redirect=true&ov_redirect=true",
        "website_url": "https://www.boat-lifestyle.com/products/airdopes-161?_gl=1*10jxa4r*_gcl_aw*R0NMLjE3OTAwNzYwMDkuQ2owS0NRand6c2pWQmhDM0FSSXNBTG5NdjRtR0JLSFo4RGJNTllFV3NiVDJwV2txZFhqWUZnOTZQeWU1a2RTRXMzVFYxaDhvZGlOWEx4a2FBc21CRUFMd193Y0I.*_gcl_au*NTYzMTE5MjI2LjE3OTAwNzYwMDkuLS4tLjE3OTAwNzYwMDguMTg1MDA4MTY4OS4xNzkwMDc2MDA5LjE3OTAwNzYwMDg.",
        "playstore_app_id": None,
        "reddit_query": "boAt Airdopes TWS earbuds",
    },

    # ------------------------------------------------------------------ #
    # Product 3: boAt Wave (smartwatches)
    # ------------------------------------------------------------------ #
    "wave": {
        "name": "boAt Wave Smartwatch",
        "amazon_url": "https://www.amazon.in/portal/customer-reviews/B0FLF44GTQ/ref=cm_cr_dp_d_show_all_top?_encoding=UTF8&ie=UTF8&reviewerType=all_reviews",
        "flipkart_url": "https://www.flipkart.com/boat-wave-fury-smartwatch/p/itm7795a986a347e?pid=SMWGQHN4GNAVXD8H&lid=LSTSMWGQHN4GNAVXD8HLTJ7ZZ&marketplace=FLIPKART&q=boAt+WATCH&store=ajy%2Fbuh&srno=s_1_5&otracker=search&otracker1=search&fm=Search&iid=b3b08f93-9878-4e6e-b568-015fc07b72c4.SMWGQHN4GNAVXD8H.SEARCH&ppt=sp&ppn=sp&ssid=3j0k6vlf4w0000001790076129627&qH=961f6689ca0e4dcb&ov_redirect=true",
        "website_url": "https://www.boat-lifestyle.com/products/boat-chrome-ivory-amoled-display-smartwatch",
        "playstore_app_id": None,
        "reddit_query": "boAt Wave smartwatch",
    },

    # ------------------------------------------------------------------ #
    # HOW TO ADD MORE PRODUCTS -- copy this block and fill in your values:
    # ------------------------------------------------------------------ #
    # "storm": {
    #     "name": "boAt Storm Smartwatch",
    #     "amazon_url": "PASTE_AMAZON_REVIEW_URL_HERE",
    #     "playstore_app_id": None,
    #     "reddit_query": "boAt Storm smartwatch",
    # },
}

# All boAt apps found on Play Store
BOAT_LIFESTYLE_APP_ID = "com.coffye.khjenr"   # boAt Shopping
BOAT_ALL_APP_IDS = [
    ("com.coffye.khjenr",   "boAt Shopping"),
    ("com.boAt.wristgear",  "boAt Wearables"),
    ("com.boAt.hearables",  "boAt Hearables"),
    ("com.coveiot.android.boat", "boAt Crest"),
    ("com.boat.Xtend.two",  "boAt Wave"),
]
