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
    page_title="boAt | Hardware Intelligence & Sentiment Hub",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- boAt Premium Dark Glassmorphism CSS with Scroll Animations ---
st.markdown("""
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css"/>
</head>
<style>
    /* Global Typography & Deep Dark Background */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .stApp {
        background: radial-gradient(circle at 15% 15%, #180507 0%, #0a0c10 50%, #05070a 100%);
        background-attachment: fixed;
        color: #f1f5f9;
    }

    /* Scroll Animations & Smooth Behavior */
    html {
        scroll-behavior: smooth;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translate3d(0, 30px, 0);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
        }
    }
    
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(230, 0, 0, 0.4); }
        50% { box-shadow: 0 0 30px rgba(255, 51, 51, 0.7); }
        100% { box-shadow: 0 0 15px rgba(230, 0, 0, 0.4); }
    }

    .scroll-reveal {
        animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Header / Hero Banner Styling */
    .boat-hero {
        background: linear-gradient(135deg, rgba(230, 0, 0, 0.95) 0%, rgba(120, 0, 0, 0.9) 60%, rgba(20, 5, 8, 0.95) 100%);
        backdrop-filter: blur(12px);
        padding: 36px 40px;
        border-radius: 20px;
        margin-bottom: 28px;
        border: 1px solid rgba(255, 77, 77, 0.35);
        box-shadow: 0 20px 40px rgba(230, 0, 0, 0.25);
        position: relative;
        overflow: hidden;
    }
    .boat-hero::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 350px;
        height: 350px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0) 70%);
        transform: rotate(45deg);
        pointer-events: none;
    }
    .boat-hero h1 {
        color: #ffffff !important;
        font-weight: 800;
        font-size: 2.4rem;
        letter-spacing: -0.5px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .boat-hero p {
        color: #f8fafc !important;
        font-size: 1.15rem;
        font-weight: 400;
        max-width: 850px;
        opacity: 0.95;
    }
    .boat-badge {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.4);
        padding: 6px 16px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 1.5px;
        display: inline-block;
        text-transform: uppercase;
    }

    /* Sidebar Glassmorphism */
    section[data-testid="stSidebar"] {
        background-color: rgba(14, 18, 27, 0.85) !important;
        backdrop-filter: blur(16px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Metric Cards - Modern Glassmorphism & Hover Micro-interactions */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, rgba(26, 32, 46, 0.7) 0%, rgba(15, 20, 30, 0.8) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px 20px;
        transition: all 0.35s ease;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        border-color: rgba(230, 0, 0, 0.5);
        box-shadow: 0 14px 32px rgba(230, 0, 0, 0.25);
    }
    div[data-testid="stMetricValue"] {
        color: #ff3333 !important;
        font-weight: 800 !important;
        font-size: 2.1rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Glass Cards Wrapper for Charts */
    .chart-card {
        background: linear-gradient(145deg, rgba(20, 26, 38, 0.6) 0%, rgba(12, 16, 25, 0.7) 100%);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 24px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .chart-card:hover {
        border-color: rgba(230, 0, 0, 0.3);
        transform: translateY(-3px);
    }

    /* Custom Section Headers */
    .section-header {
        font-size: 1.45rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 10px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-header span {
        background: linear-gradient(90deg, #ff3333, #ff6666);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Streamlit DataFrame & Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Custom Dividers */
    hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
        margin: 32px 0 !important;
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
<div class="boat-hero scroll-reveal">
    <div class="boat-badge">🎧 boAt INTELLIGENCE HUB</div>
    <h1>Hardware & Customer Sentiment Intelligence</h1>
    <p>Real-time AI Decision-Support Dashboard across E-Commerce, Retail & Social Channels</p>
</div>
""", unsafe_allow_html=True)

if DATA_PATH == SAMPLE_PATH:
    st.warning("⚠️ Showing sample dataset. Run orchestrator for live scraped data.")
else:
    mtime = os.path.getmtime(DATA_PATH)
    st.caption(f"🔄 **Pipeline Status**: Live Dataset Updated at **{datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')}**")

# --- Sidebar Filters ---
st.sidebar.markdown("## 🎛️ Interactive Filters")
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
st.markdown('<div class="scroll-reveal">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Reviews Analyzed", f"{len(filtered):,}")

pos_pct = (filtered["sentiment_label"] == "positive").mean() * 100 if len(filtered) else 0
neg_pct = (filtered["sentiment_label"] == "negative").mean() * 100 if len(filtered) else 0
avg_score = filtered["sentiment_score"].mean() if len(filtered) else 0

col2.metric("Positive Sentiment", f"{pos_pct:.1f}%")
col3.metric("Negative Friction", f"{neg_pct:.1f}%")
col4.metric("Avg Sentiment Index", f"{avg_score:.2f}")
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- GenAI Executive Summary ---
if SUMMARY_PATH.exists():
    st.markdown("""
    <div class="section-header scroll-reveal">
        <span>💡 GenAI Executive Synthesis & Hardware Recommendations</span>
    </div>
    """, unsafe_allow_html=True)
    with st.container():
        st.info(SUMMARY_PATH.read_text())
    st.divider()

# Color Map boAt Premium Style
COLOR_MAP = {
    "positive": "#00e676",
    "negative": "#ff1744",
    "neutral": "#90a4ae"
}

# --- Visual Analytics Row 1 ---
st.markdown('<div class="scroll-reveal">', unsafe_allow_html=True)
left, right = st.columns(2)

with left:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><span>Overall Sentiment Breakdown</span></div>', unsafe_allow_html=True)
    sentiment_counts = filtered["sentiment_label"].value_counts().reset_index()
    sentiment_counts.columns = ["sentiment", "count"]
    fig1 = px.pie(
        sentiment_counts,
        names="sentiment",
        values="count",
        color="sentiment",
        color_discrete_map=COLOR_MAP,
        hole=0.45
    )
    fig1.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f1f5f9", family="Plus Jakarta Sans"),
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><span>Sentiment Distribution by Product Line (%)</span></div>', unsafe_allow_html=True)
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
        font=dict(color="#f1f5f9", family="Plus Jakarta Sans"),
        xaxis_title="",
        yaxis_title="Percentage (%)",
        yaxis=dict(range=[0, 100]),
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- Visual Analytics Row 2 ---
st.markdown('<div class="scroll-reveal">', unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><span>Recurring Customer Hardware Themes</span></div>', unsafe_allow_html=True)
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
            color_discrete_sequence=["#ff3333"]
        )
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f1f5f9", family="Plus Jakarta Sans"),
            yaxis_title="",
            xaxis_title="Number of Mentions",
            yaxis=dict(autorange="reversed"),
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><span>Sentiment Breakdown by Channel (%)</span></div>', unsafe_allow_html=True)
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
        font=dict(color="#f1f5f9", family="Plus Jakarta Sans"),
        xaxis_title="",
        yaxis_title="Percentage (%)",
        yaxis=dict(range=[0, 100]),
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- Sentiment Trend ---
if "date" in filtered.columns and filtered["date"].notna().any():
    st.markdown('<div class="chart-card scroll-reveal">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><span>📈 Sentiment Dynamics Over Time</span></div>', unsafe_allow_html=True)
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
    fig5.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f1f5f9", family="Plus Jakarta Sans"),
        xaxis_title="Date",
        yaxis_title="Daily Reviews",
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig5, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

# --- Actionable Flagged Reviews ---
st.markdown('<div class="scroll-reveal">', unsafe_allow_html=True)
st.markdown('<div class="section-header"><span>🚨 Priority Action Items — Severe Negative Hardware Feedback</span></div>', unsafe_allow_html=True)
flagged = filtered[filtered["sentiment_label"] == "negative"].sort_values("sentiment_score").head(15)
st.dataframe(
    flagged[["product", "source", "topic_label", "sentiment_score", "review_text"]],
    use_container_width=True,
    hide_index=True
)
st.markdown('</div>', unsafe_allow_html=True)

# --- Data Explorer ---
with st.expander("🔍 Explore Full Raw Dataset"):
    st.dataframe(filtered, use_container_width=True)


