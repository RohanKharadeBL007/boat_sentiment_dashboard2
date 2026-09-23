"""
End-to-end pipeline: merge scraped CSVs -> preprocess -> sentiment -> topics
-> save processed output for the dashboard.

Usage:
    python run_pipeline.py --inputs data/playstore_reviews.csv data/amazon_reviews.csv data/reddit_mentions.csv --n_topics 6
"""

import argparse
from pipeline.preprocessing import load_and_merge, preprocess_dataframe
from pipeline.sentiment_analysis import add_sentiment
from pipeline.topic_modeling import run_lda


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True,
                         help="Paths to raw scraped CSVs to merge")
    parser.add_argument("--n_topics", type=int, default=6)
    parser.add_argument("--sentiment_method", default="vader", choices=["vader", "transformer"])
    parser.add_argument("--min_df", type=int, default=5,
                         help="Lower this (e.g. 2) if your corpus is small")
    parser.add_argument("--out", default="outputs/processed_reviews.csv")
    args = parser.parse_args()

    print("Loading and merging sources...")
    df = load_and_merge(args.inputs)
    print(f"  {len(df)} reviews after merge/dedup")

    print("Preprocessing text...")
    df = preprocess_dataframe(df)
    print(f"  {len(df)} reviews after cleaning")

    print(f"Scoring sentiment ({args.sentiment_method})...")
    df = add_sentiment(df, method=args.sentiment_method)
    print(df["sentiment_label"].value_counts().to_string())

    print(f"Extracting {args.n_topics} topics...")
    topic_keywords, df = run_lda(df, n_topics=args.n_topics, min_df=args.min_df)
    for idx, words in topic_keywords.items():
        print(f"  Topic {idx}: {', '.join(words)}")

    df.to_csv(args.out, index=False)
    print(f"\nSaved processed data to {args.out}")
    print("Now run: cd dashboard && streamlit run app.py")
    print(f"(update DATA_PATH in app.py to point to {args.out} if needed)")


if __name__ == "__main__":
    main()
