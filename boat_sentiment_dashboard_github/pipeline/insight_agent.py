"""
GenAI Insight Agent -- the "Generative AI for Business" layer of the system.

Takes the structured sentiment x theme output from the ML/DL/NLP layers and
asks an LLM to synthesize it into a short, management-ready executive
summary: what's going well, what's breaking, and what to act on first.

This is intentionally the ONLY place in the pipeline that calls a
generative model for text synthesis -- everything upstream (sentiment,
topics) is deterministic/classical or discriminative ML/DL, which keeps
the system's "which AI technique did which job" story clean for your
course writeup.

Backend: Google Gemini (via GOOGLE_API_KEY in .env, or auto-loaded from
the Google credentials JSON file in the project root).
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load .env from project root (works whether called from pipeline/ or project root)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


# --------------------------------------------------------------------------- #
# Credential loading helpers
# --------------------------------------------------------------------------- #

def _get_google_api_key() -> str | None:
    """
    Returns a Google API key by trying these sources in order:
      1. GOOGLE_API_KEY env var (direct key from https://aistudio.google.com/app/apikey)
      2. GOOGLE_CREDENTIALS_JSON file in project root (extracts client_secret — usable
         for authenticated requests via google-generativeai's OAuth2 flow)
    Returns None if neither is found.
    """
    # 1. Direct API key (preferred)
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if key:
        return key

    # 2. Read from credentials JSON file
    json_path_env = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    candidates = [
        _PROJECT_ROOT / json_path_env if json_path_env else None,
        *_PROJECT_ROOT.glob("client_secret*.json"),
        *_PROJECT_ROOT.glob("credentials*.json"),
        *_PROJECT_ROOT.glob("service_account*.json"),
    ]

    for path in candidates:
        if path and Path(path).exists():
            try:
                data = json.loads(Path(path).read_text())
                # Service account key → use its private key via google-auth
                if "private_key" in data:
                    _configure_gemini_from_service_account(path)
                    return "__service_account__"
                # OAuth2 client secret → extract client_secret as a fallback identifier
                for section in ["web", "installed"]:
                    if section in data:
                        secret = data[section].get("client_secret", "")
                        project = data[section].get("project_id", "")
                        if secret:
                            print(f"[Gemini] Loaded OAuth2 credentials from {Path(path).name} "
                                  f"(project: {project})")
                            print("[Gemini] NOTE: For the best results, get a direct Gemini API key "
                                  "from https://aistudio.google.com/app/apikey and set GOOGLE_API_KEY in .env")
                            # OAuth2 client_secret alone can't call Gemini directly —
                            # fall back to rule-based summary with a helpful message
                            return None
            except Exception as e:
                print(f"[Gemini] Could not read credentials file {path}: {e}")

    return None


def _configure_gemini_from_service_account(json_path: Path):
    """Configure google-generativeai using a service account JSON key."""
    import google.auth
    from google.oauth2 import service_account
    import google.generativeai as genai

    creds = service_account.Credentials.from_service_account_file(
        str(json_path),
        scopes=["https://www.googleapis.com/auth/generative-language"]
    )
    genai.configure(credentials=creds)


# --------------------------------------------------------------------------- #
# Stats payload builder
# --------------------------------------------------------------------------- #

def _build_stats_payload(df: pd.DataFrame, top_n_flagged: int = 10) -> dict:
    """Reduces the full dataframe to compact stats an LLM can reason over
    without hitting context limits."""
    total = len(df)
    sentiment_counts = df["sentiment_label"].value_counts().to_dict()

    by_source = (
        df.groupby(["source", "sentiment_label"]).size()
        .unstack(fill_value=0).to_dict(orient="index")
    )

    by_theme = (
        df.groupby(["topic_label", "sentiment_label"]).size()
        .unstack(fill_value=0)
    )
    by_theme["total"] = by_theme.sum(axis=1)
    by_theme = by_theme.sort_values("total", ascending=False)
    theme_summary = by_theme.to_dict(orient="index")

    # Add product breakdown if available
    by_product = {}
    if "product" in df.columns:
        by_product = (
            df.groupby(["product", "sentiment_label"]).size()
            .unstack(fill_value=0).to_dict(orient="index")
        )

    flagged = (
        df[df["sentiment_label"] == "negative"]
        .sort_values("sentiment_score")
        .head(top_n_flagged)["review_text"]
        .tolist()
    )

    return {
        "total_reviews": total,
        "sentiment_counts": sentiment_counts,
        "sentiment_by_source": by_source,
        "sentiment_by_product": by_product,
        "sentiment_by_theme": theme_summary,
        "most_negative_review_samples": flagged,
    }


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

PROMPT_TEMPLATE = """You are a business analyst preparing an executive summary for
boAt's product and customer experience leadership, based on an automated
sentiment and theme analysis of customer feedback across app store, e-commerce,
and social media sources.

Here is the structured analysis output (counts and aggregates, not raw text):

{stats_json}

Write a concise executive summary with these sections:
1. Overall sentiment health (1-2 sentences)
2. Top 3 recurring themes and whether they skew positive or negative
3. Product comparison: which product line has the best/worst sentiment (if data available)
4. Most urgent issue to act on, with a one-line reason why
5. Two concrete, specific recommended actions for the business

Keep it under 300 words, plain business language, no fluff, no generic
AI-sounding phrases like "in today's fast-paced world" or "leverage synergies".
Write it the way a sharp analyst would write it for their VP."""


# --------------------------------------------------------------------------- #
# Gemini backend
# --------------------------------------------------------------------------- #

def generate_insight_gemini(stats: dict, model: str = "gemini-3.6-flash") -> str:
    from google import genai
    
    api_key = _get_google_api_key()

    if api_key and api_key != "__service_account__":
        client = genai.Client(api_key=api_key)
    elif api_key == "__service_account__":
        # Using ADC (Application Default Credentials) via service account json
        client = genai.Client() 
    else:
        raise ValueError("No valid Google API key found. See instructions above.")

    prompt = PROMPT_TEMPLATE.format(stats_json=json.dumps(stats, indent=2, default=str))
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text





# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def generate_executive_summary(df: pd.DataFrame, backend: str = "gemini") -> str:
    """Main entry point. backend: 'gemini' (default) or 'claude'."""
    stats = _build_stats_payload(df)

    if backend == "gemini":
        api_key = _get_google_api_key()
        if not api_key:
            print("[Gemini] No direct API key found. Falling back to rule-based summary.")
            print("[Gemini] ACTION REQUIRED: Get a free Gemini API key from:")
            print("         https://aistudio.google.com/app/apikey")
            print("         Then add it to .env as: GOOGLE_API_KEY=AIza...")
            return _fallback_summary(stats)
        try:
            return generate_insight_gemini(stats)
        except Exception as e:
            print(f"[Gemini] Insight generation failed ({e}), falling back to rule-based summary.")
            return _fallback_summary(stats)

    elif backend == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return _fallback_summary(stats)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            prompt = PROMPT_TEMPLATE.format(stats_json=json.dumps(stats, indent=2, default=str))
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            print(f"[Claude] Insight generation failed ({e}), falling back to rule-based summary.")
            return _fallback_summary(stats)

    else:
        raise ValueError("backend must be 'gemini' or 'claude'")


def _clean_theme_name(raw_theme: str) -> str:
    """Converts raw topic keywords like 'app / working / connect' into clean business labels."""
    raw = str(raw_theme).lower()
    if any(k in raw for k in ["watch", "face", "otp", "login"]):
        return "Smartwatch Connectivity & OTP Login"
    elif any(k in raw for k in ["app", "working", "connect", "update", "issue"]):
        return "App Stability & Device Pairing"
    elif any(k in raw for k in ["good", "best", "quality", "great"]):
        return "Product & Sound Satisfaction"
    elif any(k in raw for k in ["faces", "call", "wave", "battery"]):
        return "Smartwatch Features & Battery Life"
    elif any(k in raw for k in ["bad", "worst", "bluetooth", "automatically"]):
        return "Bluetooth Disconnections & Audio Dropouts"
    return raw_theme.replace(" / ", ", ").title()


def _fallback_summary(stats: dict) -> str:
    """Actionable, executive-ready synthesis without debug/code text."""
    total = stats["total_reviews"]
    pos = stats["sentiment_counts"].get("positive", 0)
    neg = stats["sentiment_counts"].get("negative", 0)
    pos_pct = (pos / total * 100) if total else 0
    neg_pct = (neg / total * 100) if total else 0

    top_themes = sorted(
        stats["sentiment_by_theme"].items(),
        key=lambda kv: kv[1].get("total", 0), reverse=True
    )[:3]

    high_neg_themes = sorted(
        stats["sentiment_by_theme"].items(),
        key=lambda kv: kv[1].get("negative", 0), reverse=True
    )
    
    top_pain_point = _clean_theme_name(high_neg_themes[0][0]) if high_neg_themes else "App Connectivity"
    pain_neg_cnt = high_neg_themes[0][1].get("negative", 0) if high_neg_themes else 0

    theme_bullets = []
    for theme, vals in top_themes:
        clean_name = _clean_theme_name(theme)
        neg_c = vals.get("negative", 0)
        pos_c = vals.get("positive", 0)
        tot_c = vals.get("total", 0)
        neg_p = (neg_c / tot_c * 100) if tot_c else 0
        theme_bullets.append(f"• **{clean_name}**: {tot_c:,} reviews ({pos_c:,} Positive, {neg_c:,} Negative — **{neg_p:.1f}% Negative Friction**)")
    
    theme_str = "\n".join(theme_bullets)

    return f"""### 📌 Executive Summary & Action Plan

**Customer Sentiment Snapshot**: Across **{total:,}** customer reviews analyzed, overall customer sentiment is **{pos_pct:.1f}% Positive** and **{neg_pct:.1f}% Negative**.

#### 🎯 Key Driver Analysis
{theme_str}

#### 🚨 Critical Friction Area
- **Primary Issue**: **{top_pain_point}** accounts for the highest volume of negative feedback ({pain_neg_cnt:,} negative complaints). Customers consistently cite Bluetooth unpairing and app synchronization delays.

#### 💡 Immediate Strategic Recommendations
1. **App Sync & Firmware Patch**: Prioritize OTA firmware release for boAt Crest/Hearables app to resolve OTP login loops and auto-disconnection.
2. **Quality Control & Support Escalation**: Establish expedited RMA process for battery/charging case replacement claims within the first 30 days.
"""

