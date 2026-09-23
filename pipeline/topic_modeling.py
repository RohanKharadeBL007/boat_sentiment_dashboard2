"""
Theme/topic extraction from cleaned review text.

Default: LDA via scikit-learn -- lightweight, no extra downloads, fast
enough for coursework-scale data (thousands to tens of thousands of
reviews), and produces interpretable keyword-per-topic output.

Optional: BERTopic -- generally produces more coherent, human-readable
topics because it uses embeddings + clustering rather than bag-of-words,
but is heavier (needs sentence-transformers + umap + hdbscan) and slower.
Worth switching to this for the final deliverable if runtime allows.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation


def run_lda(df: pd.DataFrame, text_col: str = "topic_text",
            n_topics: int = 6, n_top_words: int = 10, random_state: int = 42,
            min_df=5, max_df=0.9):
    """Fits LDA and returns (topic_keywords, doc_topic_df).

    min_df/max_df default to sensible values for a large corpus
    (thousands of reviews). For small test runs (under a few hundred
    docs), pass min_df=2 or an integer/float appropriate to your corpus
    size, or CountVectorizer will filter out nearly all vocabulary.
    """
    texts = df[text_col].tolist()

    vectorizer = CountVectorizer(max_df=max_df, min_df=min_df, max_features=5000)
    doc_term_matrix = vectorizer.fit_transform(texts)

    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=random_state,
        learning_method="online",
        max_iter=20,
    )
    doc_topic_matrix = lda.fit_transform(doc_term_matrix)

    feature_names = vectorizer.get_feature_names_out()
    topic_keywords = {}
    for topic_idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[-n_top_words:][::-1]
        topic_keywords[topic_idx] = [feature_names[i] for i in top_indices]

    df = df.copy()
    df["dominant_topic"] = np.argmax(doc_topic_matrix, axis=1)
    df["topic_confidence"] = np.max(doc_topic_matrix, axis=1)

    # Human-readable label = top 3 keywords joined
    topic_labels = {
        idx: " / ".join(words[:3]) for idx, words in topic_keywords.items()
    }
    df["topic_label"] = df["dominant_topic"].map(topic_labels)

    return topic_keywords, df


def run_bertopic(df: pd.DataFrame, text_col: str = "cleaned_text"):
    """
    Higher-quality alternative. Requires:
        pip install bertopic sentence-transformers
    Uses raw cleaned_text (not the heavily-stripped topic_text) since
    BERTopic's embeddings benefit from natural sentence structure.
    """
    from bertopic import BERTopic

    texts = df[text_col].tolist()
    topic_model = BERTopic(language="english", calculate_probabilities=False)
    topics, _ = topic_model.fit_transform(texts)

    df = df.copy()
    df["dominant_topic"] = topics

    topic_info = topic_model.get_topic_info()
    topic_labels = dict(zip(topic_info["Topic"], topic_info["Name"]))
    df["topic_label"] = df["dominant_topic"].map(topic_labels)

    return topic_model, df
