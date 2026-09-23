"""
Interactive decision-support dashboard for boAt sentiment & theme analysis.

Run with:
    streamlit run app.py
"""

import os
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

try:
    from pipeline.insight_agent import _clean_theme_name
except ImportError:
    def _clean_theme_name(t): return str(t).replace(" / ", ", ").title()


# --- Page Config ---
st.set_page_config(
    page_title="boAt | Sentiment & Theme Intelligence",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- boAt Theme CSS Styling ---
st.markdown("""
<style>
    /* Main Background & Text Color */
    .stApp {
        background-color: #0b0e14;
        color: #f1f5f9;
    }
    
    /* Header / Banner Styling */
    .boat-header {
        background: linear-gradient(135deg, #e60000 0%, #800000 100%);
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(230, 0, 0, 0.3);
        border: 1px solid #ff3333;
    }
    .boat-header h1 {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800;
        letter-spacing: 1px;
        margin: 0;
    }
    .boat-header p {
        color: #f8fafc !important;
        font-size: 1.05rem;
        margin-top: 6px;
        margin-bottom: 0;
    }
    .boat-badge {
        background-color: #ffffff;
        color: #e60000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #121824 !important;
        border-right: 1px solid #1e293b;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #e60000 !important;
        font-weight: 700;
    }
    div[data-testid="metric-container"] {
        background-color: #161e2e;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    
    /* Dividers */
    hr {
        border-color: #1e293b !important;
    }
    
    /* Table Header */
    .dataframe th {
        background-color: #1e293b !important;
        color: #e60000 !important;
    }
</style>
""", unsafe_allow_html=True)

# Data paths
LATEST_PATH = Path(__file__).parent.parent / "outputs" / "processed_reviews_latest.csv"
SAMPLE_PATH = Path(__file__).parent.parent / "outputs" / "processed_sample.csv"
DATA_PATH = LATEST_PATH if LATEST_PATH.exists() else SAMPLE_PATH
SUMMARY_PATH = Path(__file__).parent.parent / "outputs" / "executive_summary_latest.txt"

KNOWN_PRODUCTS = [
    "boAt Rockerz",
    "boAt Airdopes",
    "boAt Wave Smartwatch"
]

@st.cache_data(ttl=60)
def load_data(path):
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # Backfill product if missing / null or generic
    def fill_product(row):
        p = str(row.get("product", ""))
        if pd.isna(row.get("product")) or p == "nan" or not p.strip():
            txt = str(row.get("review_text", "")).lower()
            if any(k in txt for k in ["rockerz", "headphone", "earphone", "neckband"]):
                return "boAt Rockerz"
            elif any(k in txt for k in ["airdopes", "earbud", "tws", "case", "charging"]):
                return "boAt Airdopes"
            elif any(k in txt for k in ["watch", "wave", "dial", "display", "step", "heart", "smartwatch"]):
                return "boAt Wave Smartwatch"
            return "boAt General / Multi-category"
        return p
    
    df["product"] = df.apply(fill_product, axis=1)
    df["source"] = df["source"].fillna("Other Channel")
    df["sentiment_label"] = df["sentiment_label"].fillna("neutral")
    return df

df = load_data(DATA_PATH)

# --- Header Banner ---
st.markdown("""
<div class="boat-header">
    <div class="boat-badge">boAt INTELLIGENCE HUB</div>
    <h1>boAt — Customer Sentiment & Theme Intelligence</h1>
    <p>Real-time AI Decision-Support Dashboard across E-Commerce, App Store & Social Feedback</p>
</div>
""", unsafe_allow_html=True)

if DATA_PATH == SAMPLE_PATH:
    st.warning("⚠️ Showing sample dataset. Run orchestrator for live scraped data.")
else:
    mtime = os.path.getmtime(DATA_PATH)
    st.caption(f"🔄 **Pipeline Status**: Last updated at **{datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')}**")

# --- Sidebar Filters ---
st.sidebar.markdown("## 🎛️ Filter Controls")
st.sidebar.markdown("---")

# 1. Product Filter (boAt Products)
all_prods = sorted([str(p) for p in df["product"].dropna().unique()])
selected_prods = st.sidebar.multiselect(
    "🎧 Select Product Line",
    options=all_prods,
    default=all_prods,
    help="Filter feedback by boAt product series (Rockerz, Airdopes, Wave Smartwatches)"
)

# 2. Source Filter
all_sources = sorted([str(s) for s in df["source"].dropna().unique()])
selected_sources = st.sidebar.multiselect(
    "🌐 Feedback Source",
    options=all_sources,
    default=all_sources
)

# 3. Sentiment Filter
all_sentiments = sorted([str(st_lbl) for st_lbl in df["sentiment_label"].dropna().unique()])
selected_sentiments = st.sidebar.multiselect(
    "📊 Sentiment Category",
    options=all_sentiments,
    default=all_sentiments
)

# Active Filtering logic with fallback for empty selections
filtered = df.copy()

if selected_prods:
    filtered = filtered[filtered["product"].isin(selected_prods)]
else:
    st.sidebar.info("💡 Select at least one Product Line to view data.")

if selected_sources:
    filtered = filtered[filtered["source"].isin(selected_sources)]
else:
    st.sidebar.info("💡 Select at least one Feedback Source to view data.")

if selected_sentiments:
    filtered = filtered[filtered["sentiment_label"].isin(selected_sentiments)]
else:
    st.sidebar.info("💡 Select at least one Sentiment Category to view data.")


# --- Top KPI Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Reviews Analyzed", f"{len(filtered):,}")

pos_pct = (filtered["sentiment_label"] == "positive").mean() * 100 if len(filtered) else 0
neg_pct = (filtered["sentiment_label"] == "negative").mean() * 100 if len(filtered) else 0
avg_score = filtered["sentiment_score"].mean() if len(filtered) else 0

col2.metric("Positive Sentiment %", f"{pos_pct:.1f}%")
col3.metric("Negative Sentiment %", f"{neg_pct:.1f}%")
col4.metric("Avg Sentiment Index", f"{avg_score:.2f}")

st.divider()

# --- GenAI Executive Summary ---
if SUMMARY_PATH.exists():
    st.subheader("💡 GenAI Executive Synthesis")
    with st.container():
        st.info(SUMMARY_PATH.read_text())
    st.divider()

# Color Map boAt Style
COLOR_MAP = {
    "positive": "#00c853",
    "negative": "#ff1744",
    "neutral": "#90a4ae"
}

# --- Visual Analytics Row 1 ---
left, right = st.columns(2)

with left:
    st.subheader("Overall Sentiment Breakdown")
    sentiment_counts = filtered["sentiment_label"].value_counts().reset_index()
    sentiment_counts.columns = ["sentiment", "count"]
    fig1 = px.pie(
        sentiment_counts,
        names="sentiment",
        values="count",
        color="sentiment",
        color_discrete_map=COLOR_MAP,
        hole=0.4
    )
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f1f5f9")
    st.plotly_chart(fig1, use_container_width=True)

with right:
    st.subheader("Sentiment Distribution by Product Line (%)")
    by_prod = filtered.groupby(["product", "sentiment_label"]).size().reset_index(name="count")
    prod_totals = by_prod.groupby("product")["count"].transform("sum")
    by_prod["percentage"] = (by_prod["count"] / prod_totals) * 100
    
    fig2 = px.bar(
        by_prod,
        x="product",
        y="percentage",
        color="sentiment_label",
        barmode="stack",
        color_discrete_map=COLOR_MAP,
        hover_data={"count": True, "percentage": ":.1f}%"}
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1f5f9",
        xaxis_title="",
        yaxis_title="Percentage (%)",
        yaxis=dict(range=[0, 100])
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- Visual Analytics Row 2 ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Recurring Customer Themes")
    if "topic_label" in filtered.columns:
        theme_counts = filtered["topic_label"].value_counts().reset_index().head(8)
        theme_counts.columns = ["theme", "count"]
        # Clean up theme labels for display
        theme_counts["clean_theme"] = theme_counts["theme"].apply(_clean_theme_name)
        fig3 = px.bar(
            theme_counts,
            x="count",
            y="clean_theme",
            orientation="h",
            color_discrete_sequence=["#e60000"]
        )
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f1f5f9",
            yaxis_title="",
            xaxis_title="Number of Mentions",
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig3, use_container_width=True)

with c2:
    st.subheader("Sentiment Distribution by Channel (%)")
    by_source = filtered.groupby(["source", "sentiment_label"]).size().reset_index(name="count")
    source_totals = by_source.groupby("source")["count"].transform("sum")
    by_source["percentage"] = (by_source["count"] / source_totals) * 100
    
    fig4 = px.bar(
        by_source,
        x="source",
        y="percentage",
        color="sentiment_label",
        barmode="stack",
        color_discrete_map=COLOR_MAP,
        hover_data={"count": True, "percentage": ":.1f}%"}
    )
    fig4.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1f5f9",
        xaxis_title="",
        yaxis_title="Percentage (%)",
        yaxis=dict(range=[0, 100])
    )
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# --- Sentiment Trend ---
if "date" in filtered.columns and filtered["date"].notna().any():
    st.subheader("📈 Sentiment Dynamics Over Time")
    trend = filtered.dropna(subset=["date"]).copy()
    trend["date_only"] = trend["date"].dt.date
    trend_agg = trend.groupby(["date_only", "sentiment_label"]).size().reset_index(name="count")
    fig5 = px.line(
        trend_agg,
        x="date_only",
        y="count",
        color="sentiment_label",
        color_discrete_map=COLOR_MAP
    )
    fig5.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f1f5f9", xaxis_title="Date", yaxis_title="Daily Reviews")
    st.plotly_chart(fig5, use_container_width=True)
    st.divider()

# --- Actionable Flagged Reviews ---
st.subheader("🚨 Priority Action Items — Severe Negative Feedback")
flagged = filtered[filtered["sentiment_label"] == "negative"].sort_values("sentiment_score").head(15)
st.dataframe(
    flagged[["product", "source", "topic_label", "sentiment_score", "review_text"]],
    use_container_width=True,
    hide_index=True
)

# --- Data Explorer ---
with st.expander("🔍 Explore Raw Dataset"):
    st.dataframe(filtered, use_container_width=True)

