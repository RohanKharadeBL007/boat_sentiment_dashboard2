"""
Cleans and normalizes raw review/social text before sentiment and topic
modeling. Keeps the cleaning light -- transformer sentiment models work
better on natural text than heavily stripped text, so we preserve
punctuation and case for the sentiment step, and produce a separate
heavily-cleaned column for topic modeling.
"""

import re
import pandas as pd


def basic_clean(text: str) -> str:
    """Light cleaning: fix whitespace, strip URLs/emails, keep punctuation."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def deep_clean_for_topics(text: str, stopwords: set) -> str:
    """Heavier cleaning for topic modeling: lowercase, strip punctuation/numbers,
    remove stopwords and very short tokens."""
    text = basic_clean(text).lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = [t for t in text.split() if t not in stopwords and len(t) > 2]
    return " ".join(tokens)


def load_and_merge(csv_paths: list[str]) -> pd.DataFrame:
    """Load multiple source CSVs (play store / e-commerce / social) and merge
    into one standard schema: review_text, rating, date, source, product."""
    dfs = []
    for path in csv_paths:
        df = pd.read_csv(path)
        for col in ["review_text", "rating", "date", "source", "product"]:
            if col not in df.columns:
                df[col] = None
        dfs.append(df[["review_text", "rating", "date", "source", "product"]])
    merged = pd.concat(dfs, ignore_index=True)
    merged = merged.dropna(subset=["review_text"])
    merged = merged[merged["review_text"].str.strip() != ""]
    merged = merged.drop_duplicates(subset=["review_text"])
    return merged.reset_index(drop=True)


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Adds cleaned_text (light) and topic_text (heavy) columns."""
    try:
        import nltk
        from nltk.corpus import stopwords as nltk_stopwords
        nltk.download("stopwords", quiet=True)
        stop_words = set(nltk_stopwords.words("english"))
    except Exception:
        # Fallback minimal stopword list if NLTK data unavailable
        stop_words = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "in", "on", "at", "to", "for", "of", "with", "this", "that", "it",
            "i", "my", "me", "you", "your", "very", "just", "not", "have",
            "has", "had", "be", "been", "will", "would", "can", "could",
        }

    df = df.copy()
    df["cleaned_text"] = df["review_text"].apply(basic_clean)
    df["topic_text"] = df["cleaned_text"].apply(lambda t: deep_clean_for_topics(t, stop_words))
    df = df[df["cleaned_text"].str.len() > 3].reset_index(drop=True)
    return df
