"""
Sentiment scoring for cleaned review text.

Two options are provided:
1. VADER (default) -- fast, no model download, works well on short
   review-style text with slang/emoji/punctuation cues. Good enough for
   a first pass and for large volumes.
2. HuggingFace transformer (optional, slower, more accurate on nuanced
   text) -- enable with use_transformer=True. Requires `transformers`
   and `torch` installed, and will download a model on first run.
"""

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def score_with_vader(df: pd.DataFrame, text_col: str = "cleaned_text") -> pd.DataFrame:
    analyzer = SentimentIntensityAnalyzer()
    df = df.copy()

    def classify(text):
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        return pd.Series({"sentiment_score": compound, "sentiment_label": label})

    sentiment_df = df[text_col].apply(classify)
    return pd.concat([df, sentiment_df], axis=1)


def score_with_transformer(df: pd.DataFrame, text_col: str = "cleaned_text",
                            batch_size: int = 32) -> pd.DataFrame:
    """
    Uses a HuggingFace sentiment pipeline. Slower but often more accurate,
    especially on sarcasm/nuance VADER misses. Recommended once you have
    real data and want a second opinion, or for a smaller high-value
    subset (e.g. 1-star / 5-star reviews) rather than the full corpus.
    """
    from transformers import pipeline

    clf = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        truncation=True,
    )
    df = df.copy()
    texts = df[text_col].tolist()

    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results.extend(clf(batch))

    df["sentiment_label"] = [r["label"].lower() for r in results]
    df["sentiment_score"] = [
        r["score"] if r["label"] == "POSITIVE" else -r["score"] for r in results
    ]
    return df


def add_sentiment(df: pd.DataFrame, method: str = "vader") -> pd.DataFrame:
    if method == "vader":
        return score_with_vader(df)
    elif method == "transformer":
        return score_with_transformer(df)
    else:
        raise ValueError("method must be 'vader' or 'transformer'")
