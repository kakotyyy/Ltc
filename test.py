import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
import zipfile
from datetime import date, timedelta

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

# ---------------------------------------------------------
# Technical Indicators Helpers
# ---------------------------------------------------------
def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    high = df['High'].values.astype(float)
    low = df['Low'].values.astype(float)
    close = df['Close'].values.astype(float)
    n = len(df)
    
    if HAS_TALIB:
        atr = talib.ATR(high, low, close, timeperiod=period)
    else:
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr[0] = high[0] - low[0]
        atr = pd.Series(tr).rolling(window=period).mean().values

    hl2 = (high + low) / 2.0
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    in_uptrend = np.ones(n, dtype=bool)
    supertrend = np.full(n, np.nan)

    for i in range(1, n):
        if np.isnan(atr[i]):
            continue
        if close[i-1] > upperband[i-1]:
            upperband[i] = upperband[i]
        else:
            upperband[i] = min(upperband[i], upperband[i-1]) if not np.isnan(upperband[i-1]) else upperband[i]

        if close[i-1] < lowerband[i-1]:
            lowerband[i] = lowerband[i]
        else:
            lowerband[i] = max(lowerband[i], lowerband[i-1]) if not np.isnan(lowerband[i-1]) else lowerband[i]

        if close[i] > upperband[i-1]:
            in_uptrend[i] = True
        elif close[i] < lowerband[i-1]:
            in_uptrend[i] = False
        else:
            in_uptrend[i] = in_uptrend[i-1]

        supertrend[i] = lowerband[i] if in_uptrend[i] else upperband[i]

    return supertrend, in_uptrend


def calculate_adx(df: pd.DataFrame, period: int = 14):
    high = df['High'].values.astype(float)
    low = df['Low'].values.astype(float)
    close = df['Close'].values.astype(float)

    if HAS_TALIB:
        return talib.ADX(high, low, close, timeperiod=period)
    
    n = len(df)
    if n < period * 2:
        return np.full(n, np.nan)

    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = high[0] - low[0]

    up_move = high - np.roll(high, 1)
    down_move = np.roll(low, 1) - low
    up_move[0] = 0
    down_move[0] = 0

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = pd.Series(tr).ewm(alpha=1.0/period, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1.0/period, adjust=False).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1.0/period, adjust=False).mean() / atr)

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    adx = dx.ewm(alpha=1.0/period, adjust=False).mean().values
    return adx


# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dalal Street Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# Modern Sleek Dark FinTech Theme with Groww Mint Accent (#00d09c) & Serif Headings
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,500;0,600;0,700;0,800;1,600&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    /* Serif Typography for Brand & Headings with Vibrant Gradient Fills */
    h1, h2, h3, h4, .serif-font, .brand-title span, .neon-card-title, .hero-terminal-title, .gradient-heading {
        font-family: 'Playfair Display', 'Newsreader', Georgia, serif !important;
        letter-spacing: -0.3px;
    }

    /* Gradient Fills for Headings using Accent Colors */
    .hero-terminal-title {
        font-size: 3.2rem;
        font-weight: 800;
        margin-bottom: 8px;
        line-height: 1.15;
        background: linear-gradient(135deg, #ffffff 15%, #00d09c 45%, #a855f7 75%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .gradient-header-text {
        font-family: 'Playfair Display', 'Newsreader', Georgia, serif !important;
        background: linear-gradient(135deg, #ffffff 20%, #00d09c 50%, #ec4899 90%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
        margin-bottom: 6px;
    }

    .brand-title span {
        background: linear-gradient(135deg, #ffffff 30%, #00d09c 70%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Overall dark canvas */
    .stApp {
        background-color: #080a0f;
        background-image: 
            radial-gradient(circle at 15% 10%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 85% 15%, rgba(0, 208, 156, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 50% 80%, rgba(236, 72, 153, 0.05) 0%, transparent 50%);
        color: #e2e8f0;
    }

    /* Top Navigation Header */
    .nav-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 0 20px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        margin-bottom: 24px;
    }
    .brand-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.45rem;
        font-weight: 700;
    }
    .brand-accent-box {
        width: 32px;
        height: 32px;
        border-radius: 9px;
        background: linear-gradient(135deg, #00d09c 0%, #a855f7 50%, #ec4899 100%);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: 800;
        font-size: 15px;
        box-shadow: 0 0 16px rgba(168, 85, 247, 0.45);
    }
    .badge-live {
        background: linear-gradient(135deg, rgba(0, 208, 156, 0.15), rgba(168, 85, 247, 0.15));
        color: #00d09c;
        border: 1px solid rgba(0, 208, 156, 0.3);
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        box-shadow: 0 0 12px rgba(0, 208, 156, 0.2);
    }

    /* Home Hero Header Center Aligned */
    .home-hero-center {
        text-align: center;
        margin: 20px auto 40px auto;
        max-width: 800px;
    }
    .hero-terminal-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        font-weight: 400;
        letter-spacing: 0.2px;
    }

    /* Large Neon Glow Cards for Home Screen */
    .neon-card {
        position: relative;
        background: linear-gradient(160deg, #121622 0%, #0d1017 100%);
        border-radius: 20px;
        padding: 38px 28px 30px 28px;
        min-height: 280px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        text-align: center;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
    }
    .neon-glow-green {
        border: 1px solid rgba(0, 208, 156, 0.3);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(0, 208, 156, 0.2);
    }
    .neon-glow-green:hover {
        border-color: #00d09c;
        box-shadow: 0 0 45px -5px rgba(0, 208, 156, 0.5), 0 12px 35px rgba(0, 0, 0, 0.7);
        transform: translateY(-5px);
    }

    .neon-glow-gradient {
        border: 1px solid rgba(168, 85, 247, 0.35);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(236, 72, 153, 0.2);
    }
    .neon-glow-gradient:hover {
        border-color: #d946ef;
        box-shadow: 0 0 45px -5px rgba(217, 70, 239, 0.5), 0 12px 35px rgba(0, 0, 0, 0.7);
        transform: translateY(-5px);
    }

    .neon-glow-pink {
        border: 1px solid rgba(236, 72, 153, 0.3);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(236, 72, 153, 0.2);
    }
    .neon-glow-pink:hover {
        border-color: #ec4899;
        box-shadow: 0 0 45px -5px rgba(236, 72, 153, 0.5), 0 12px 35px rgba(0, 0, 0, 0.7);
        transform: translateY(-5px);
    }

    .neon-glow-cyan {
        border: 1px solid rgba(6, 182, 212, 0.35);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(6, 182, 212, 0.2);
    }
    .neon-glow-cyan:hover {
        border-color: #06b6d4;
        box-shadow: 0 0 45px -5px rgba(6, 182, 212, 0.5), 0 12px 35px rgba(0, 0, 0, 0.7);
        transform: translateY(-5px);
    }

    .neon-glow-amber {
        border: 1px solid rgba(245, 158, 11, 0.3);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(245, 158, 11, 0.2);
    }
    .neon-glow-amber:hover {
        border-color: #f59e0b;
        box-shadow: 0 0 45px -5px rgba(245, 158, 11, 0.5), 0 12px 35px rgba(0, 0, 0, 0.7);
        transform: translateY(-5px);
    }

    /* Rounded Corner Square Filter Tiles with Light Accent Gradients */
    .filter-tile-card {
        border-radius: 16px;
        padding: 12px 14px 10px 14px;
        margin-top: 4px;
        margin-bottom: 8px;
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(255, 255, 255, 0.08);
        user-select: none;
    }
    .filter-tile-selected {
        border-color: #00d09c !important;
        border-width: 1.5px !important;
        box-shadow: 0 0 25px rgba(0, 208, 156, 0.4), inset 0 0 15px rgba(0, 208, 156, 0.06) !important;
    }
    .tile-gradient-mint {
        background: linear-gradient(145deg, rgba(0, 208, 156, 0.12) 0%, rgba(18, 22, 34, 0.95) 75%);
    }
    .tile-gradient-mint.tile-active {
        border-color: rgba(0, 208, 156, 0.55);
    }
    .tile-gradient-purple {
        background: linear-gradient(145deg, rgba(168, 85, 247, 0.12) 0%, rgba(18, 22, 34, 0.95) 75%);
    }
    .tile-gradient-purple.tile-active {
        border-color: rgba(168, 85, 247, 0.55);
    }
    .tile-gradient-pink {
        background: linear-gradient(145deg, rgba(236, 72, 153, 0.12) 0%, rgba(18, 22, 34, 0.95) 75%);
    }
    .tile-gradient-pink.tile-active {
        border-color: rgba(236, 72, 153, 0.55);
    }
    .tile-gradient-cyan {
        background: linear-gradient(145deg, rgba(6, 182, 212, 0.12) 0%, rgba(18, 22, 34, 0.95) 75%);
    }
    .tile-gradient-cyan.tile-active {
        border-color: rgba(6, 182, 212, 0.55);
    }
    .tile-gradient-amber {
        background: linear-gradient(145deg, rgba(245, 158, 11, 0.12) 0%, rgba(18, 22, 34, 0.95) 75%);
    }
    .tile-gradient-amber.tile-active {
        border-color: rgba(245, 158, 11, 0.55);
    }

    /* Interactive tile trigger button */
    .stButton.tile-action-btn button {
        width: 100% !important;
        border-radius: 10px !important;
        padding: 5px 10px !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #94a3b8 !important;
        margin-top: 4px !important;
        transition: all 0.2s ease !important;
    }
    .stButton.tile-action-btn button:hover {
        background: rgba(0, 208, 156, 0.12) !important;
        border-color: rgba(0, 208, 156, 0.4) !important;
        color: #00d09c !important;
    }
    .stButton.tile-action-selected button {
        background: linear-gradient(135deg, rgba(0, 208, 156, 0.2), rgba(168, 85, 247, 0.2)) !important;
        border-color: #00d09c !important;
        color: #00d09c !important;
        box-shadow: 0 0 14px rgba(0, 208, 156, 0.35) !important;
    }

    .tile-header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 2px;
    }
    .tile-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.2px;
    }
    .tile-tag {
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 8px;
        letter-spacing: 0.3px;
    }

    /* Side-by-side Configuration Panel */
    .filter-config-panel {
        background: rgba(18, 22, 34, 0.95);
        border: 1px solid rgba(0, 208, 156, 0.35);
        border-radius: 18px;
        padding: 22px 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.55), 0 0 20px rgba(0, 208, 156, 0.15);
        min-height: 380px;
    }

    .neon-card-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 16px;
    }
    .badge-green {
        background: rgba(0, 208, 156, 0.12);
        color: #00d09c;
        border: 1px solid rgba(0, 208, 156, 0.25);
    }
    .badge-gradient {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(236, 72, 153, 0.15));
        color: #e879f9;
        border: 1px solid rgba(217, 70, 239, 0.3);
    }
    .badge-pink {
        background: rgba(236, 72, 153, 0.12);
        color: #f472b6;
        border: 1px solid rgba(236, 72, 153, 0.25);
    }
    .badge-cyan {
        background: rgba(6, 182, 212, 0.12);
        color: #06b6d4;
        border: 1px solid rgba(6, 182, 212, 0.3);
    }
    .badge-amber {
        background: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .neon-card-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.3px;
        margin-bottom: 10px;
    }
    .neon-card-desc {
        font-size: 0.9rem;
        color: #94a3b8;
        line-height: 1.55;
        margin-bottom: 12px;
        max-width: 280px;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #11151f !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(168, 85, 247, 0.3) !important;
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.45rem !important;
    }

    /* Buttons with Neon Glow */
    button[kind="primary"] {
        background: linear-gradient(135deg, #00d09c 0%, #059669 100%) !important;
        color: #080a0f !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 9px !important;
        padding: 9px 22px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 14px rgba(0, 208, 156, 0.25) !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #00e5ab 0%, #00d09c 100%) !important;
        box-shadow: 0 0 22px rgba(0, 208, 156, 0.55) !important;
        transform: translateY(-1px) !important;
    }
    button[kind="secondary"] {
        background: #131722 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #cbd5e1 !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: #d946ef !important;
        color: #f0abfc !important;
        box-shadow: 0 0 14px rgba(217, 70, 239, 0.3) !important;
    }

    /* Export CSV Button - Bigger, Bolder with Green to Pink Gradient */
    .export-csv-wrapper {
        margin: 16px 0 18px 0;
    }
    .export-csv-wrapper button {
        background: linear-gradient(135deg, #00d09c 0%, #a855f7 50%, #ec4899 100%) !important;
        color: #ffffff !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        padding: 14px 34px !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 22px rgba(0, 208, 156, 0.35), 0 0 25px rgba(236, 72, 153, 0.25) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: uppercase !important;
    }
    .export-csv-wrapper button:hover {
        background: linear-gradient(135deg, #00e5ab 0%, #c084fc 50%, #f472b6 100%) !important;
        box-shadow: 0 0 32px rgba(0, 208, 156, 0.5), 0 0 32px rgba(236, 72, 153, 0.45) !important;
        transform: translateY(-2px) scale(1.02) !important;
        color: #ffffff !important;
    }
    div[data-testid="stExpander"] {
        border-radius: 14px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    /* 1. Yellow / Gold Amber Gradient */
    div[data-testid="stExpander"]:nth-of-type(6n+1) {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(180, 83, 9, 0.1) 100%) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+1):hover {
        border-color: #fbbf24 !important;
        box-shadow: 0 0 25px rgba(245, 158, 11, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+1) .streamlit-expanderHeader:hover {
        color: #fbbf24 !important;
    }

    /* 2. Crimson / Coral Red Gradient */
    div[data-testid="stExpander"]:nth-of-type(6n+2) {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(185, 28, 28, 0.1) 100%) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+2):hover {
        border-color: #f87171 !important;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+2) .streamlit-expanderHeader:hover {
        color: #f87171 !important;
    }

    /* 3. Electric Blue / Cyan Gradient */
    div[data-testid="stExpander"]:nth-of-type(6n+3) {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(14, 165, 233, 0.1) 100%) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+3):hover {
        border-color: #60a5fa !important;
        box-shadow: 0 0 25px rgba(59, 130, 246, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+3) .streamlit-expanderHeader:hover {
        color: #60a5fa !important;
    }

    /* 4. Mint Green (Groww signature) */
    div[data-testid="stExpander"]:nth-of-type(6n+4) {
        background: linear-gradient(135deg, rgba(0, 208, 156, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(5, 150, 105, 0.1) 100%) !important;
        border: 1px solid rgba(0, 208, 156, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+4):hover {
        border-color: #00e5ab !important;
        box-shadow: 0 0 25px rgba(0, 208, 156, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+4) .streamlit-expanderHeader:hover {
        color: #00e5ab !important;
    }

    /* 5. Violet / Purple Gradient */
    div[data-testid="stExpander"]:nth-of-type(6n+5) {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(126, 34, 206, 0.1) 100%) !important;
        border: 1px solid rgba(168, 85, 247, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+5):hover {
        border-color: #c084fc !important;
        box-shadow: 0 0 25px rgba(168, 85, 247, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+5) .streamlit-expanderHeader:hover {
        color: #c084fc !important;
    }

    /* 6. Neon Pink / Magenta Gradient */
    div[data-testid="stExpander"]:nth-of-type(6n+6) {
        background: linear-gradient(135deg, rgba(236, 72, 153, 0.14) 0%, rgba(20, 24, 33, 0.96) 65%, rgba(190, 24, 93, 0.1) 100%) !important;
        border: 1px solid rgba(236, 72, 153, 0.3) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+6):hover {
        border-color: #f472b6 !important;
        box-shadow: 0 0 25px rgba(236, 72, 153, 0.35), 0 8px 24px rgba(0, 0, 0, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stExpander"]:nth-of-type(6n+6) .streamlit-expanderHeader:hover {
        color: #f472b6 !important;
    }

    .streamlit-expanderHeader {
        background: transparent !important;
        color: #f1f5f9 !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
        letter-spacing: -0.2px !important;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
    }
    div[data-testid="stExpander"] > div[role="region"] {
        border-top: 1px solid rgba(255, 255, 255, 0.07) !important;
        padding-top: 16px !important;
    }

    /* Clean Stock Tag Pill */
    .ticker-pill {
        display: inline-block;
        background: linear-gradient(135deg, rgba(0, 208, 156, 0.08), rgba(168, 85, 247, 0.08));
        color: #00d09c;
        border: 1px solid rgba(0, 208, 156, 0.25);
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 3px;
        letter-spacing: 0.3px;
    }

    /* Inputs dark styling */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #141824 !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="input"] > div:hover {
        border-color: rgba(168, 85, 247, 0.4) !important;
    }

    /* Container Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1200px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Popular NSE Stocks Directory
# ---------------------------------------------------------
POPULAR_NSE_STOCKS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro",
    "TATAMOTORS": "Tata Motors",
    "HINDUNILVR": "Hindustan Unilever",
    "BAJFINANCE": "Bajaj Finance",
    "MARUTI": "Maruti Suzuki",
    "WIPRO": "Wipro"
}

# ---------------------------------------------------------
# Session State Init
# ---------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if "stock_data" not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.query_info = None

if "screener_cache" not in st.session_state:
    st.session_state.screener_cache = None
if "screener_raw_tickers" not in st.session_state:
    st.session_state.screener_raw_tickers = []
if "screener_filename" not in st.session_state:
    st.session_state.screener_filename = None
if "active_tile" not in st.session_state:
    st.session_state.active_tile = None
if "heatmap_raw_tickers" not in st.session_state:
    st.session_state.heatmap_raw_tickers = []
if "heatmap_filename" not in st.session_state:
    st.session_state.heatmap_filename = None


# ---------------------------------------------------------
# Helper function to fetch data
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=300)
def load_stock_data(ticker: str, start: date, end: date, interval: str):
    download_end = end + timedelta(days=1)
    df = yf.download(
        tickers=ticker,
        start=start.strftime("%Y-%m-%d"),
        end=download_end.strftime("%Y-%m-%d"),
        interval=interval,
        progress=False,
        auto_adjust=False
    )
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df = df.reset_index()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    elif "Datetime" in df.columns:
        df.rename(columns={"Datetime": "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df


# ---------------------------------------------------------
# Helper function to fetch Heatmap data (cached)
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=600)
def fetch_heatmap_data(symbols_tuple: tuple, timeframe_choice: str):
    """
    Fetches historical OHLCV and market cap data for a set of symbols, cached for fast user experience.
    """
    symbols = list(symbols_tuple)
    if not symbols:
        return pd.DataFrame()

    period_map = {
        "Daily": "10d",
        "Weekly": "1mo",
        "Monthly": "3mo",
        "Quarterly": "6mo",
        "Six-Monthly": "1y",
        "Yearly": "2y"
    }
    fetch_period = period_map.get(timeframe_choice, "1y")

    try:
        data = yf.download(
            tickers=symbols,
            period=fetch_period,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=True
        )
    except Exception:
        data = pd.DataFrame()

    tickers_obj = None
    try:
        tickers_obj = yf.Tickers(" ".join(symbols))
    except Exception:
        pass

    results = []

    for sym in symbols:
        close_series = None
        vol_val = 0
        
        if not data.empty and "Close" in data:
            if isinstance(data["Close"], pd.DataFrame) and sym in data["Close"].columns:
                close_series = data["Close"][sym].dropna()
                if "Volume" in data and sym in data["Volume"].columns:
                    v_s = data["Volume"][sym].dropna()
                    if not v_s.empty:
                        vol_val = float(v_s.iloc[-1])
            elif isinstance(data["Close"], pd.Series):
                close_series = data["Close"].dropna()
                if "Volume" in data:
                    v_s = data["Volume"].dropna()
                    if not v_s.empty:
                        vol_val = float(v_s.iloc[-1])

        # Fallback to single download if missing
        if close_series is None or len(close_series) < 2:
            try:
                single_df = yf.download(sym, period=fetch_period, interval="1d", progress=False, auto_adjust=False)
                if not single_df.empty:
                    if isinstance(single_df.columns, pd.MultiIndex):
                        single_df.columns = [c[0] if isinstance(c, tuple) else c for c in single_df.columns]
                    close_series = single_df["Close"].dropna()
                    if "Volume" in single_df.columns:
                        vol_val = float(single_df["Volume"].dropna().iloc[-1]) if not single_df["Volume"].dropna().empty else 0
            except Exception:
                pass

        if close_series is None or len(close_series) < 2:
            continue

        current_price = float(close_series.iloc[-1])

        # Determine reference price based on timeframe
        # Approx trading days: Daily=1, Weekly=5, Monthly=21, Quarterly=63, Six-Monthly=126, Yearly=252
        bars_back_map = {
            "Daily": 1,
            "Weekly": 5,
            "Monthly": 21,
            "Quarterly": 63,
            "Six-Monthly": 126,
            "Yearly": 252
        }
        bars_back = bars_back_map.get(timeframe_choice, 1)
        ref_idx = max(0, len(close_series) - 1 - bars_back)
        ref_price = float(close_series.iloc[ref_idx])

        if ref_price > 0:
            pct_change = ((current_price - ref_price) / ref_price) * 100.0
        else:
            pct_change = 0.0

        # Retrieve market cap
        mcap = 0.0
        if tickers_obj and hasattr(tickers_obj, "tickers") and sym in tickers_obj.tickers:
            try:
                t_inst = tickers_obj.tickers[sym]
                fast_mc = getattr(t_inst.fast_info, "market_cap", None)
                if fast_mc is not None and not np.isnan(fast_mc) and fast_mc > 0:
                    mcap = float(fast_mc)
            except Exception:
                pass

        if mcap <= 0:
            mcap = current_price * (vol_val if vol_val > 0 else 1000000.0)

        clean_symbol = sym.replace(".NS", "").replace(".BO", "")
        category = "Gainers" if pct_change >= 0 else "Losers"

        results.append({
            "ticker": clean_symbol,
            "full_symbol": sym,
            "price": current_price,
            "pct_change": round(pct_change, 2),
            "market_cap": round(mcap, 2),
            "volume": vol_val,
            "category": category
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------
# Top Header Bar
# ---------------------------------------------------------
st.markdown("""
<div class="nav-header">
    <div class="brand-title">
        <div class="brand-accent-box">▲</div>
        <span>Dalal Street Terminal</span>
    </div>
    <div>
        <span class="badge-live">Live Markets</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Screen Routing
# ---------------------------------------------------------
if st.session_state.current_page == "Home":
    # Center-aligned Hero Branding
    st.markdown("""
    <div class="home-hero-center">
        <div class="hero-terminal-title">Dalal Street Terminal</div>
        <div class="hero-terminal-subtitle">High-Performance Market Intelligence, Technical Screening & Backtesting</div>
    </div>
    """, unsafe_allow_html=True)

    # 4 Large Neon Glow Cards (Center Aligned)
    col_c1, col_c2, col_c3, col_c4 = st.columns(4, gap="medium")
    
    with col_c1:
        st.markdown("""
        <div class="neon-card neon-glow-green">
            <div>
                <span class="neon-card-badge badge-green">OHLC • Analysis</span>
                <div class="neon-card-title">Stock Data</div>
                <div class="neon-card-desc">Interactive charts, historical data and CSV export.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #00d09c; letter-spacing: 0.5px;">EXPLORE →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Stock Data", key="btn_nav_stock", type="primary", use_container_width=True):
            st.session_state.current_page = "Download Stock Data"
            st.rerun()

    with col_c2:
        st.markdown("""
        <div class="neon-card neon-glow-gradient">
            <div>
                <span class="neon-card-badge badge-gradient">Multi-Stock • TA</span>
                <div class="neon-card-title">Screener</div>
                <div class="neon-card-desc">Screen with Moving Averages, Supertrend, RSI, MACD & ADX.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #e879f9; letter-spacing: 0.5px;">FILTER →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Screener", key="btn_nav_screener", type="primary", use_container_width=True):
            st.session_state.current_page = "Screener"
            st.rerun()

    with col_c3:
        st.markdown("""
        <div class="neon-card neon-glow-cyan">
            <div>
                <span class="neon-card-badge badge-cyan">Market • Treemap</span>
                <div class="neon-card-title">Heatmap</div>
                <div class="neon-card-desc">Visualize market breadth across Gainers, Losers & Market Cap.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #06b6d4; letter-spacing: 0.5px;">VISUALIZE →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Heatmap", key="btn_nav_heatmap", type="primary", use_container_width=True):
            st.session_state.current_page = "Heatmap"
            st.rerun()

    with col_c4:
        st.markdown("""
        <div class="neon-card neon-glow-pink">
            <div>
                <span class="neon-card-badge badge-pink">Strategy • Simulation</span>
                <div class="neon-card-title">Backtest</div>
                <div class="neon-card-desc">Simulate historical strategies, win-rates and drawdowns.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #f472b6; letter-spacing: 0.5px;">SIMULATE →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Backtest", key="btn_nav_backtest", type="secondary", use_container_width=True):
            st.session_state.current_page = "Backtest"
            st.rerun()


elif st.session_state.current_page == "Heatmap":
    top_nav_h1, top_nav_h2 = st.columns([1, 6])
    with top_nav_h1:
        if st.button("← Back", key="heatmap_home_back"):
            st.session_state.current_page = "Home"
            st.rerun()
    with top_nav_h2:
        st.markdown("<h2 class='gradient-header-text'>Market Heatmap</h2>", unsafe_allow_html=True)

    # 2 Sub-Cards: Historical & Live
    sub_col1, sub_col2 = st.columns(2, gap="large")

    with sub_col1:
        st.markdown("""
        <div class="neon-card neon-glow-cyan" style="min-height: 250px;">
            <div>
                <span class="neon-card-badge badge-cyan">Custom Portfolio • Multi-TF</span>
                <div class="neon-card-title">Historical Heatmap</div>
                <div class="neon-card-desc">Upload ticker CSV to visualize market performance across Gainers, Losers & Market Cap across various timeframes.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #06b6d4; letter-spacing: 0.5px;">VIEW HEATMAP →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Historical Heatmap", key="btn_nav_heatmap_hist", type="primary", use_container_width=True):
            st.session_state.current_page = "Heatmap_Historical"
            st.rerun()

    with sub_col2:
        st.markdown("""
        <div class="neon-card neon-glow-amber" style="min-height: 250px;">
            <div>
                <span class="neon-card-badge badge-amber">Real-time Stream</span>
                <div class="neon-card-title">Live Heatmap</div>
                <div class="neon-card-desc">Streaming intra-day live tick data and live sector tree maps.</div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #f59e0b; letter-spacing: 0.5px;">LIVE FEED →</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Open Live Heatmap", key="btn_nav_heatmap_live", type="secondary", use_container_width=True):
            st.session_state.current_page = "Heatmap_Live"
            st.rerun()


# ---------------------------------------------------------
# LIVE HEATMAP PAGE (UNDER CONSTRUCTION)
# ---------------------------------------------------------
elif st.session_state.current_page == "Heatmap_Live":
    top_nav_l1, top_nav_l2 = st.columns([1, 6])
    with top_nav_l1:
        if st.button("← Back", key="heatmap_live_back"):
            st.session_state.current_page = "Heatmap"
            st.rerun()
    with top_nav_l2:
        st.markdown("<h2 class='gradient-header-text'>Live Market Heatmap</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div class="neon-card neon-glow-amber" style="margin-top: 16px; padding: 48px; text-align: center; align-items: center;">
        <span class="neon-card-badge badge-amber">Under Construction</span>
        <div class="neon-card-title" style="margin-top: 14px; font-size: 1.8rem;">Live Heatmap Under Construction</div>
        <div class="neon-card-desc" style="max-width: 560px; margin: 12px auto; font-size: 0.95rem; color: #94a3b8;">
            Live tick websocket stream and real-time intraday heatmap visualizer is currently under construction. Please check back soon or explore the Historical Heatmap!
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# HISTORICAL HEATMAP PAGE
# ---------------------------------------------------------
elif st.session_state.current_page == "Heatmap_Historical":
    top_nav_hh1, top_nav_hh2 = st.columns([1, 6])
    with top_nav_hh1:
        if st.button("← Back", key="heatmap_hist_back"):
            st.session_state.current_page = "Heatmap"
            st.rerun()
    with top_nav_hh2:
        st.markdown("<h2 class='gradient-header-text'>Historical Market Heatmap</h2>", unsafe_allow_html=True)

    # File Uploader and Controls in an Expander
    with st.expander("Tickers & Heatmap Settings", expanded=(len(st.session_state.heatmap_raw_tickers) == 0)):
        col_hu1, col_hu2 = st.columns([2, 1])
        with col_hu1:
            hm_uploaded_file = st.file_uploader("Upload CSV containing stock tickers", type=["csv"], key="heatmap_uploader")
            # 30 liquid Nifty 50 sample stocks
            nifty_30_sample = [
                "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
                "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "MARUTI", "BAJFINANCE",
                "AXISBANK", "SUNPHARMA", "TITAN", "KOTAKBANK", "ULTRACEMCO", "WIPRO",
                "NTPC", "POWERGRID", "HINDUNILVR", "JSWSTEEL", "TATASTEEL", "ADANIENT",
                "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "NESTLEIND", "ONGC", "M&M"
            ]

            sample_btn_col1, sample_btn_col2 = st.columns([1.2, 1])
            with sample_btn_col1:
                if st.button("🚀 Run Sample Stocks (30 Nifty Stocks)", key="btn_run_sample_stocks", use_container_width=True):
                    st.session_state.heatmap_raw_tickers = nifty_30_sample
                    st.session_state.heatmap_filename = "Nifty 50 (30 Sample Stocks)"
                    st.rerun()
            with sample_btn_col2:
                if st.session_state.heatmap_filename:
                    if st.button("🔄 Reset Portfolio", key="btn_reset_hm_stocks", use_container_width=True):
                        st.session_state.heatmap_raw_tickers = []
                        st.session_state.heatmap_filename = None
                        st.rerun()

            if st.session_state.heatmap_filename:
                st.caption(f"✓ Active Portfolio: **{st.session_state.heatmap_filename}** ({len(st.session_state.heatmap_raw_tickers)} stocks)")
        with col_hu2:
            hm_exchange = st.selectbox("Exchange Suffix", ["NSE (.NS)", "BSE (.BO)", "US / None"], index=0, key="hm_exchange")

        if hm_uploaded_file is not None:
            try:
                hm_uploaded_file.seek(0)
                csv_df = pd.read_csv(hm_uploaded_file)
                found_col = None
                for col_name in ["symbol", "ticker", "stock", "symbols", "tickers", "stocks", "name", "tradingsymbol"]:
                    for actual_col in csv_df.columns:
                        if str(actual_col).strip().lower() == col_name:
                            found_col = actual_col
                            break
                    if found_col:
                        break
                if found_col is None:
                    found_col = csv_df.columns[0]

                parsed_tickers = (
                    csv_df[found_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .tolist()
                )
                parsed_tickers = [t for t in parsed_tickers if t and t not in ["SYMBOL", "TICKER", "STOCK", "NAME"]]
                if parsed_tickers:
                    st.session_state.heatmap_raw_tickers = parsed_tickers
                    st.session_state.heatmap_filename = hm_uploaded_file.name
                    st.rerun()
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")

    # Fallback to default 30 Nifty sample stocks if nothing loaded yet
    current_tickers = st.session_state.heatmap_raw_tickers
    if not current_tickers:
        current_tickers = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
            "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "MARUTI", "BAJFINANCE",
            "AXISBANK", "SUNPHARMA", "TITAN", "KOTAKBANK", "ULTRACEMCO", "WIPRO",
            "NTPC", "POWERGRID", "HINDUNILVR", "JSWSTEEL", "TATASTEEL", "ADANIENT",
            "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "NESTLEIND", "ONGC", "M&M"
        ]

    # Format tickers according to exchange
    def format_hm_ticker(tick: str, ex_setting: str) -> str:
        tick = tick.strip().upper()
        if "NSE" in ex_setting and not tick.endswith(".NS"):
            return f"{tick.split('.')[0]}.NS"
        elif "BSE" in ex_setting and not tick.endswith(".BO"):
            return f"{tick.split('.')[0]}.BO"
        return tick

    formatted_symbols = [format_hm_ticker(t, hm_exchange) for t in current_tickers]
    formatted_symbols = list(dict.fromkeys(formatted_symbols))  # Remove duplicates

    # Heatmap Controls Bar
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        timeframe_choice = st.selectbox(
            "Timeframe",
            ["Daily", "Weekly", "Monthly", "Quarterly", "Six-Monthly", "Yearly"],
            index=0,
            key="hm_timeframe"
        )
    with ctrl_col2:
        slice_by = st.selectbox(
            "Slice by",
            ["Gainers", "Losers", "Market Cap"],
            index=0,
            key="hm_slice_by"
        )

    # Fetch cached data
    with st.spinner("Fetching and caching stock performance data..."):
        hm_df = fetch_heatmap_data(tuple(formatted_symbols), timeframe_choice)

    if hm_df.empty:
        st.warning("No price data retrieved for the selected stocks. Please verify ticker symbols.")
    else:
        # Filter / Slice dataframe and set box sizing directly based on Slice by
        if slice_by == "Gainers":
            filtered_df = hm_df[hm_df["pct_change"] >= 0].copy()
            if filtered_df.empty:
                st.info("No gainers found for the selected timeframe. Showing all stocks.")
                filtered_df = hm_df.copy()
            filtered_df["box_size"] = filtered_df["pct_change"].apply(lambda x: max(abs(x), 0.05))
        elif slice_by == "Losers":
            filtered_df = hm_df[hm_df["pct_change"] < 0].copy()
            if filtered_df.empty:
                st.info("No losers found for the selected timeframe. Showing all stocks.")
                filtered_df = hm_df.copy()
            filtered_df["box_size"] = filtered_df["pct_change"].apply(lambda x: max(abs(x), 0.05))
        else:  # Market Cap
            filtered_df = hm_df.copy()
            filtered_df["box_size"] = filtered_df["market_cap"].apply(lambda x: max(float(x), 1.0))

        # Market Summary Stat Pills
        total_stocks = len(filtered_df)
        total_gainers = len(filtered_df[filtered_df["pct_change"] >= 0])
        total_losers = len(filtered_df[filtered_df["pct_change"] < 0])
        avg_change = filtered_df["pct_change"].mean() if not filtered_df.empty else 0.0

        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        stat_col1.metric("Stocks Displayed", f"{total_stocks}")
        stat_col2.metric("Gainers (▲)", f"{total_gainers}", delta=f"{total_gainers}/{total_stocks}")
        stat_col3.metric("Losers (▼)", f"{total_losers}", delta=f"-{total_losers}", delta_color="inverse")
        stat_col4.metric("Avg Change", f"{avg_change:+.2f}%", delta=f"{avg_change:+.2f}%")

        # Human readable format for tooltip
        def format_mcap_display(val):
            if val >= 1e12:
                return f"₹{val / 1e12:.2f}T"
            elif val >= 1e7:
                return f"₹{val / 1e7:.2f}Cr"
            return f"₹{val:,.0f}"

        filtered_df["mcap_formatted"] = filtered_df["market_cap"].apply(format_mcap_display)
        filtered_df["change_label"] = filtered_df["pct_change"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")
        filtered_df["custom_label"] = (
            filtered_df["ticker"] + "<br>" +
            "₹" + filtered_df["price"].map("{:,.2f}".format) + "<br>" +
            filtered_df["change_label"]
        )

        # Dynamic Color Scaling:
        # Gainers: least gainer = light green, top gainer = deep emerald green
        # Losers: least loser (near 0) = light red/coral, top loser (deep negative) = deep dark red
        # Mixed (Market Cap): deep red -> light red -> light green -> deep green
        if slice_by == "Gainers":
            min_p = float(filtered_df["pct_change"].min())
            max_p = float(filtered_df["pct_change"].max())
            if min_p == max_p:
                min_p = max(0.0, max_p - 1.0)
                max_p = max_p + 1.0
            range_bounds = [min_p, max_p]
            color_scale = [
                [0.0, "#a7f3d0"],  # Light pastel mint/green for least gainer
                [0.5, "#10b981"],  # Medium green
                [1.0, "#064e3b"]   # Deep emerald/forest green for top gainer
            ]
            cmid = None
        elif slice_by == "Losers":
            min_p = float(filtered_df["pct_change"].min())  # Most negative (top loser)
            max_p = float(filtered_df["pct_change"].max())  # Least negative (least loser)
            if min_p == max_p:
                min_p = min_p - 1.0
                max_p = min(0.0, max_p + 1.0)
            range_bounds = [min_p, max_p]
            color_scale = [
                [0.0, "#7f1d1d"],  # Deep crimson / dark red for top loser (most negative)
                [0.5, "#ef4444"],  # Medium red
                [1.0, "#fecaca"]   # Light soft red / pastel coral for least loser (closest to 0)
            ]
            cmid = None
        else:
            # Market Cap (contains both Gainers and Losers)
            max_abs_pct = max(float(filtered_df["pct_change"].abs().max()), 2.0)
            range_bounds = [-max_abs_pct, max_abs_pct]
            color_scale = [
                [0.0, "#7f1d1d"],  # Deep red (top loser)
                [0.35, "#ef4444"], # Medium red
                [0.48, "#fecaca"], # Light red
                [0.50, "#1e293b"], # Neutral midpoint near 0%
                [0.52, "#a7f3d0"], # Light green
                [0.70, "#10b981"], # Medium green
                [1.0, "#064e3b"]   # Deep green (top gainer)
            ]
            cmid = 0.0

        treemap_kwargs = {
            "data_frame": filtered_df,
            "path": ["ticker"],
            "values": "box_size",
            "color": "pct_change",
            "color_continuous_scale": color_scale,
            "range_color": range_bounds,
            "hover_data": {
                "box_size": False,
                "category": False,
                "ticker": True,
                "price": ":,.2f",
                "pct_change": ":+.2f",
                "mcap_formatted": True
            }
        }
        if cmid is not None:
            treemap_kwargs["color_continuous_midpoint"] = cmid

        fig_hm = px.treemap(**treemap_kwargs)

        fig_hm.update_traces(
            textinfo="label",
            texttemplate="<b>%{label}</b><br>%{customdata[2]:+.2f}%<br>₹%{customdata[1]:,.1f}",
            customdata=filtered_df[["ticker", "price", "pct_change", "mcap_formatted"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>Price: ₹%{customdata[1]:,.2f}<br>Change: %{customdata[2]:+.2f}%<br>Market Cap: %{customdata[3]}<extra></extra>",
            marker=dict(
                cornerradius=6,
                pad=dict(t=3, l=3, r=3, b=3)
            )
        )

        fig_hm.update_layout(
            template="plotly_dark",
            height=650,
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="#0c1017",
            paper_bgcolor="#0c1017",
            coloraxis_colorbar=dict(
                title=f"Change % ({timeframe_choice})",
                ticksuffix="%",
                len=0.7,
                thickness=15
            )
        )

        st.plotly_chart(fig_hm, use_container_width=True)


# ---------------------------------------------------------
# BACKTEST PLACEHOLDER PAGE
# ---------------------------------------------------------
elif st.session_state.current_page == "Backtest":
    top_nav_b1, top_nav_b2 = st.columns([1, 6])
    with top_nav_b1:
        if st.button("← Back", key="backtest_back"):
            st.session_state.current_page = "Home"
            st.rerun()
    with top_nav_b2:
        st.markdown("<h2 class='gradient-header-text'>Backtest Strategy</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div class="neon-card neon-glow-pink" style="margin-top: 16px; padding: 48px; text-align: center; align-items: center;">
        <span class="neon-card-badge badge-pink">Under Construction</span>
        <div class="neon-card-title" style="margin-top: 14px; font-size: 1.8rem;">Backtest Engine</div>
        <div class="neon-card-desc" style="max-width: 540px; margin: 12px auto; font-size: 0.95rem;">
            Strategy simulation engine will be implemented here. Backtest indicator rules, view trade logs, calculate win-rate, profit factor, and visualize equity curves.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# SCREENER PAGE
# ---------------------------------------------------------
elif st.session_state.current_page == "Screener":
    top_nav_c1, top_nav_c2 = st.columns([1, 6])
    with top_nav_c1:
        if st.button("← Back", key="scr_back"):
            st.session_state.current_page = "Home"
            st.rerun()
    with top_nav_c2:
        st.markdown("<h2 class='gradient-header-text'>Technical Screener</h2>", unsafe_allow_html=True)

    # Step 1: Upload & Settings
    with st.expander("Tickers & Exchange", expanded=(st.session_state.screener_cache is None)):
        col_u1, col_u2 = st.columns([2, 1])
        with col_u1:
            uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key="screener_uploader")
            # 30 liquid Nifty 50 sample stocks
            nifty_30_sample_screener = [
                "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
                "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "MARUTI", "BAJFINANCE",
                "AXISBANK", "SUNPHARMA", "TITAN", "KOTAKBANK", "ULTRACEMCO", "WIPRO",
                "NTPC", "POWERGRID", "HINDUNILVR", "JSWSTEEL", "TATASTEEL", "ADANIENT",
                "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "NESTLEIND", "ONGC", "M&M"
            ]

            scr_btn_col1, scr_btn_col2 = st.columns([1.2, 1])
            with scr_btn_col1:
                if st.button("🚀 Run Sample Stocks (30 Nifty Stocks)", key="btn_run_screener_sample", use_container_width=True):
                    st.session_state.screener_raw_tickers = nifty_30_sample_screener
                    st.session_state.screener_filename = "Nifty 50 (30 Sample Stocks)"
                    st.session_state.screener_cache = None
                    st.rerun()
            with scr_btn_col2:
                if st.session_state.screener_filename:
                    if st.button("🔄 Reset Portfolio", key="btn_reset_screener_stocks", use_container_width=True):
                        st.session_state.screener_raw_tickers = []
                        st.session_state.screener_filename = None
                        st.session_state.screener_cache = None
                        st.rerun()

            if st.session_state.screener_filename:
                st.caption(f"✓ Active Portfolio: **{st.session_state.screener_filename}** ({len(st.session_state.screener_raw_tickers)} stocks)")
        with col_u2:
            screener_exchange = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)", "US / None"], index=0)
            screener_timeframe = st.selectbox("Timeframe", ["Daily", "Weekly"], index=0)

        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                csv_df = pd.read_csv(uploaded_file)
                found_col = None
                for col_name in ["symbol", "ticker", "stock", "symbols", "tickers", "stocks", "name", "tradingsymbol"]:
                    for actual_col in csv_df.columns:
                        if str(actual_col).strip().lower() == col_name:
                            found_col = actual_col
                            break
                    if found_col:
                        break
                if found_col is None:
                    found_col = csv_df.columns[0]

                parsed_list = (
                    csv_df[found_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .tolist()
                )
                parsed_list = [t for t in parsed_list if t and t not in ["SYMBOL", "TICKER", "STOCK"]]
                if parsed_list:
                    st.session_state.screener_raw_tickers = parsed_list
                    st.session_state.screener_filename = uploaded_file.name
                    st.caption(f"{len(parsed_list)} tickers loaded")
            except Exception as e:
                st.error(f"Error: {e}")

        def format_screener_ticker(tick: str, ex_setting: str) -> str:
            tick = tick.strip().upper()
            if "NSE" in ex_setting and not tick.endswith(".NS"):
                return f"{tick.split('.')[0]}.NS"
            elif "BSE" in ex_setting and not tick.endswith(".BO"):
                return f"{tick.split('.')[0]}.BO"
            return tick

        formatted_tickers = [
            format_screener_ticker(t, screener_exchange)
            for t in st.session_state.screener_raw_tickers
        ]

        if formatted_tickers:
            tf_interval = "1d" if screener_timeframe == "Daily" else "1wk"
            if st.button("Fetch Data", type="primary"):
                progress_bar = st.progress(0)
                cached_data = {}
                failed_tickers = []
                lookback_days = 600 if screener_timeframe == "Daily" else 1200
                fetch_start = date.today() - timedelta(days=lookback_days)
                fetch_end = date.today()
                total_count = len(formatted_tickers)

                try:
                    raw_bulk = yf.download(
                        tickers=formatted_tickers,
                        start=fetch_start.strftime("%Y-%m-%d"),
                        end=(fetch_end + timedelta(days=1)).strftime("%Y-%m-%d"),
                        interval=tf_interval,
                        group_by='ticker',
                        progress=False,
                        auto_adjust=False,
                        threads=True
                    )

                    for idx, ticker in enumerate(formatted_tickers):
                        progress_bar.progress(int(((idx + 1) / total_count) * 100))
                        try:
                            if total_count == 1:
                                t_df = raw_bulk.copy()
                            else:
                                if hasattr(raw_bulk.columns, 'levels') and ticker in raw_bulk.columns.levels[0]:
                                    t_df = raw_bulk[ticker].dropna(how="all").copy()
                                elif ticker in raw_bulk.columns:
                                    t_df = raw_bulk[ticker].dropna(how="all").copy()
                                else:
                                    t_df = pd.DataFrame()

                            if isinstance(t_df.columns, pd.MultiIndex):
                                t_df.columns = [c[0] if isinstance(c, tuple) else c for c in t_df.columns]

                            if not t_df.empty and "Close" in t_df.columns and len(t_df.dropna(subset=["Close"])) > 5:
                                t_df = t_df.reset_index()
                                if "Date" in t_df.columns:
                                    t_df["Date"] = pd.to_datetime(t_df["Date"]).dt.tz_localize(None)
                                elif "Datetime" in t_df.columns:
                                    t_df.rename(columns={"Datetime": "Date"}, inplace=True)
                                    t_df["Date"] = pd.to_datetime(t_df["Date"]).dt.tz_localize(None)
                                cached_data[ticker] = t_df
                            else:
                                failed_tickers.append(ticker)
                        except Exception:
                            failed_tickers.append(ticker)
                except Exception as e:
                    st.error(f"Error: {e}")

                progress_bar.empty()
                if cached_data:
                    st.session_state.screener_cache = {
                        "timeframe": screener_timeframe,
                        "interval": tf_interval,
                        "data": cached_data,
                        "failed": failed_tickers,
                        "timestamp": date.today().strftime("%Y-%m-%d")
                    }
                    st.success(f"{len(cached_data)} stocks ready.")

    # Step 2: Filters & Screen
    if st.session_state.screener_cache is not None:
        cached_dict = st.session_state.screener_cache["data"]
        cache_tf = st.session_state.screener_cache["timeframe"]

        st.markdown("---")
        st.markdown("<h3 class='gradient-header-text'>Technical Filters</h3>", unsafe_allow_html=True)
        st.caption("Enable and expand filters below to configure rules.")

        # --- Filter 1: Moving Average 1 ---
        c_exp1, c_tog1 = st.columns([5.5, 1.2], gap="small")
        with c_tog1:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile1_on = st.toggle("MA 1", value=st.session_state.get("ma1_enable", True), key="ma1_enable")
        with c_exp1:
            with st.expander("Moving Average 1", expanded=st.session_state.get("ma1_enable", True)):
                c_m1_t, c_m1_l, c_m1_c = st.columns([1, 1, 2])
                with c_m1_t:
                    ma1_type = st.selectbox("Type", ["SMA", "EMA"], index=0, key="ma1_type")
                with c_m1_l:
                    ma1_length = st.number_input("Period", min_value=2, max_value=300, value=20, step=1, key="ma1_len")
                with c_m1_c:
                    ma1_cond = st.selectbox("Condition", ["Price > MA", "Price < MA"], index=0, key="ma1_cond")

        # --- Filter 2: Moving Average 2 ---
        c_exp2, c_tog2 = st.columns([5.5, 1.2], gap="small")
        with c_tog2:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile2_on = st.toggle("MA 2", value=st.session_state.get("ma2_enable", False), key="ma2_enable")
        with c_exp2:
            with st.expander("Moving Average 2", expanded=st.session_state.get("ma2_enable", False)):
                c_m2_t, c_m2_l, c_m2_c = st.columns([1, 1, 2])
                with c_m2_t:
                    ma2_type = st.selectbox("Type", ["SMA", "EMA"], index=0, key="ma2_type")
                with c_m2_l:
                    ma2_length = st.number_input("Period", min_value=2, max_value=300, value=50, step=1, key="ma2_len")
                with c_m2_c:
                    ma2_cond = st.selectbox("Condition", ["Price > MA", "Price < MA"], index=0, key="ma2_cond")

        # --- Filter 3: Moving Average 3 ---
        c_exp3, c_tog3 = st.columns([5.5, 1.2], gap="small")
        with c_tog3:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile3_on = st.toggle("MA 3", value=st.session_state.get("ma3_enable", False), key="ma3_enable")
        with c_exp3:
            with st.expander("Moving Average 3", expanded=st.session_state.get("ma3_enable", False)):
                c_m3_t, c_m3_l, c_m3_c = st.columns([1, 1, 2])
                with c_m3_t:
                    ma3_type = st.selectbox("Type", ["SMA", "EMA"], index=0, key="ma3_type")
                with c_m3_l:
                    ma3_length = st.number_input("Period", min_value=2, max_value=300, value=100, step=1, key="ma3_len")
                with c_m3_c:
                    ma3_cond = st.selectbox("Condition", ["Price > MA", "Price < MA"], index=0, key="ma3_cond")

        # --- Filter 4: Moving Average 4 ---
        c_exp4, c_tog4 = st.columns([5.5, 1.2], gap="small")
        with c_tog4:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile4_on = st.toggle("MA 4", value=st.session_state.get("ma4_enable", False), key="ma4_enable")
        with c_exp4:
            with st.expander("Moving Average 4", expanded=st.session_state.get("ma4_enable", False)):
                c_m4_t, c_m4_l, c_m4_c = st.columns([1, 1, 2])
                with c_m4_t:
                    ma4_type = st.selectbox("Type", ["SMA", "EMA"], index=0, key="ma4_type")
                with c_m4_l:
                    ma4_length = st.number_input("Period", min_value=2, max_value=300, value=200, step=1, key="ma4_len")
                with c_m4_c:
                    ma4_cond = st.selectbox("Condition", ["Price > MA", "Price < MA"], index=0, key="ma4_cond")

        # --- Filter 5: Supertrend ---
        c_exp_st, c_tog_st = st.columns([5.5, 1.2], gap="small")
        with c_tog_st:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile_st_on = st.toggle("Supertrend", value=st.session_state.get("st_enable", False), key="st_enable")
        with c_exp_st:
            with st.expander("Supertrend", expanded=st.session_state.get("st_enable", False)):
                c_st_p, c_st_m, c_st_c = st.columns([1, 1, 2])
                with c_st_p:
                    st_period = st.number_input("ATR Period", min_value=1, max_value=100, value=10, step=1, key="st_period")
                with c_st_m:
                    st_multiplier = st.number_input("Multiplier", min_value=0.5, max_value=10.0, value=3.0, step=0.5, key="st_mult")
                with c_st_c:
                    st_cond = st.selectbox("Trend", ["Bullish", "Bearish"], index=0, key="st_cond")

        # --- Filter 6: RSI ---
        c_exp_rsi, c_tog_rsi = st.columns([5.5, 1.2], gap="small")
        with c_tog_rsi:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile_rsi_on = st.toggle("RSI", value=st.session_state.get("rsi_enable", False), key="rsi_enable")
        with c_exp_rsi:
            with st.expander("RSI (Relative Strength Index)", expanded=st.session_state.get("rsi_enable", False)):
                c_rsi_p, c_rsi_cond, c_rsi_val = st.columns([1, 1.5, 1])
                with c_rsi_p:
                    rsi_period = st.number_input("Period", min_value=2, max_value=100, value=14, step=1, key="rsi_period")
                with c_rsi_cond:
                    rsi_cond = st.selectbox("Condition", ["RSI > Threshold", "RSI < Threshold"], index=0, key="rsi_cond")
                with c_rsi_val:
                    rsi_thresh = st.number_input("Threshold", min_value=1.0, max_value=99.0, value=50.0, step=5.0, key="rsi_thresh")

        # --- Filter 7: MACD ---
        c_exp_macd, c_tog_macd = st.columns([5.5, 1.2], gap="small")
        with c_tog_macd:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile_macd_on = st.toggle("MACD", value=st.session_state.get("macd_enable", False), key="macd_enable")
        with c_exp_macd:
            with st.expander("MACD", expanded=st.session_state.get("macd_enable", False)):
                macd_cond = st.selectbox(
                    "Signal Condition",
                    options=["MACD > Signal", "MACD < Signal", "Histogram > 0"],
                    index=0,
                    key="macd_cond"
                )

        # --- Filter 8: ADX ---
        c_exp_adx, c_tog_adx = st.columns([5.5, 1.2], gap="small")
        with c_tog_adx:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile_adx_on = st.toggle("ADX", value=st.session_state.get("adx_enable", False), key="adx_enable")
        with c_exp_adx:
            with st.expander("ADX (Average Directional Index)", expanded=st.session_state.get("adx_enable", False)):
                c_adx_p, c_adx_cond, c_adx_val = st.columns([1, 1.5, 1])
                with c_adx_p:
                    adx_period = st.number_input("Period", min_value=2, max_value=100, value=14, step=1, key="adx_period")
                with c_adx_cond:
                    adx_cond = st.selectbox("Condition", ["ADX > Threshold", "ADX < Threshold"], index=0, key="adx_cond")
                with c_adx_val:
                    adx_thresh = st.number_input("Threshold", min_value=1.0, max_value=99.0, value=25.0, step=5.0, key="adx_thresh")

        # --- Filter 9: % Below 52-Week High ---
        c_exp_52w, c_tog_52w = st.columns([5.5, 1.2], gap="small")
        with c_tog_52w:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            tile_52w_on = st.toggle("52W High", value=st.session_state.get("high52_enable", False), key="high52_enable")
        with c_exp_52w:
            with st.expander("% Below 52-Week High", expanded=st.session_state.get("high52_enable", False)):
                c_h52_cond, c_h52_val = st.columns([2, 1])
                with c_h52_cond:
                    high52_cond = st.selectbox("Condition", ["Within X% of 52W High (≤ X%)", "At Least X% Below 52W High (≥ X%)"], index=0, key="high52_cond")
                with c_h52_val:
                    high52_val = st.number_input("% Threshold", min_value=1.0, max_value=90.0, value=10.0, step=1.0, key="high52_val")

        # Values fallback from session state or defaults if not currently expanded
        ma1_type = st.session_state.get("ma1_type", "SMA")
        ma1_length = st.session_state.get("ma1_len", 20)
        ma1_cond = st.session_state.get("ma1_cond", "Price > MA")

        ma2_type = st.session_state.get("ma2_type", "SMA")
        ma2_length = st.session_state.get("ma2_len", 50)
        ma2_cond = st.session_state.get("ma2_cond", "Price > MA")

        ma3_type = st.session_state.get("ma3_type", "SMA")
        ma3_length = st.session_state.get("ma3_len", 100)
        ma3_cond = st.session_state.get("ma3_cond", "Price > MA")

        ma4_type = st.session_state.get("ma4_type", "SMA")
        ma4_length = st.session_state.get("ma4_len", 200)
        ma4_cond = st.session_state.get("ma4_cond", "Price > MA")

        st_period = st.session_state.get("st_period", 10)
        st_multiplier = st.session_state.get("st_mult", 3.0)
        st_cond = st.session_state.get("st_cond", "Bullish")

        rsi_period = st.session_state.get("rsi_period", 14)
        rsi_cond = st.session_state.get("rsi_cond", "RSI > Threshold")
        rsi_thresh = st.session_state.get("rsi_thresh", 50.0)

        macd_cond = st.session_state.get("macd_cond", "MACD > Signal")

        adx_period = st.session_state.get("adx_period", 14)
        adx_cond = st.session_state.get("adx_cond", "ADX > Threshold")
        adx_thresh = st.session_state.get("adx_thresh", 25.0)

        high52_cond = st.session_state.get("high52_cond", "Within X% of 52W High (≤ X%)")
        high52_val = st.session_state.get("high52_val", 10.0)



        # Logic & Sort Row
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        c_lg1, c_lg2 = st.columns(2)
        with c_lg1:
            filter_mode = st.radio("Logic", ["Match ALL (AND)", "Match ANY (OR)"], horizontal=True)
        with c_lg2:
            sort_by = st.selectbox("Sort", ["Symbol", "Price", "Change (%) High to Low", "Change (%) Low to High", "% Below 52W High"])

        active_filters_count = sum([tile1_on, tile2_on, tile3_on, tile4_on, tile_st_on, tile_rsi_on, tile_macd_on, tile_adx_on, tile_52w_on])

        if active_filters_count > 0:
            results = []
            active_ma_specs = []
            if tile1_on:
                active_ma_specs.append(("MA 1", ma1_type, int(ma1_length), ">" in ma1_cond))
            if tile2_on:
                active_ma_specs.append(("MA 2", ma2_type, int(ma2_length), ">" in ma2_cond))
            if tile3_on:
                active_ma_specs.append(("MA 3", ma3_type, int(ma3_length), ">" in ma3_cond))
            if tile4_on:
                active_ma_specs.append(("MA 4", ma4_type, int(ma4_length), ">" in ma4_cond))

            for ticker, df in cached_dict.items():
                if df is None or len(df) < 15:
                    continue

                close_series = df["Close"].dropna()
                high_series = df["High"].dropna() if "High" in df.columns else close_series
                if len(close_series) < 15:
                    continue

                close_vals = close_series.values.astype(float)
                latest_close = float(close_vals[-1])
                prev_close = float(close_vals[-2]) if len(close_vals) >= 2 else latest_close
                day_change_pct = ((latest_close - prev_close) / prev_close) * 100 if prev_close != 0 else 0

                # 52-week High Calculation
                lookback_52w = min(len(high_series), 252 if cache_tf == "Daily" else 52)
                h52 = float(high_series.iloc[-lookback_52w:].max())
                pct_below_52w = ((h52 - latest_close) / h52) * 100 if h52 > 0 else 0.0

                stock_matches = []
                info_dict = {
                    "Ticker": ticker,
                    "Symbol": ticker.replace(".NS", "").replace(".BO", ""),
                    "Price": round(latest_close, 2),
                    "Change %": round(day_change_pct, 2),
                    "52W High": round(h52, 2),
                    "% Below 52W": round(pct_below_52w, 1)
                }

                # MA Filter
                ma_err = False
                for label, m_type, m_len, is_above in active_ma_specs:
                    if len(close_vals) < m_len:
                        ma_err = True
                        break
                    if HAS_TALIB:
                        m_series = talib.SMA(close_vals, timeperiod=m_len) if m_type == "SMA" else talib.EMA(close_vals, timeperiod=m_len)
                        latest_ma = float(m_series[-1])
                    else:
                        if m_type == "SMA":
                            latest_ma = float(close_series.rolling(m_len).mean().iloc[-1])
                        else:
                            latest_ma = float(close_series.ewm(span=m_len, adjust=False).mean().iloc[-1])

                    if np.isnan(latest_ma):
                        ma_err = True
                        break

                    passed = (latest_close > latest_ma) if is_above else (latest_close < latest_ma)
                    stock_matches.append(passed)
                    info_dict[f"{label} ({m_type}{m_len})"] = round(latest_ma, 2)

                if ma_err:
                    continue

                # Supertrend Filter
                if tile_st_on:
                    if len(df) >= int(st_period) + 2:
                        try:
                            st_vals, uptrend_flags = calculate_supertrend(df, period=int(st_period), multiplier=float(st_multiplier))
                            latest_st = float(st_vals[-1])
                            is_uptrend = bool(uptrend_flags[-1])
                            target_uptrend = "Bullish" in st_cond
                            stock_matches.append(is_uptrend == target_uptrend)
                            info_dict[f"Supertrend ({int(st_period)},{st_multiplier})"] = f"₹{latest_st:,.2f} ({'Up' if is_uptrend else 'Down'})"
                        except Exception:
                            stock_matches.append(False)
                    else:
                        stock_matches.append(False)

                # RSI Filter
                if tile_rsi_on:
                    if len(close_vals) >= int(rsi_period) + 2:
                        try:
                            if HAS_TALIB:
                                rsi_series = talib.RSI(close_vals, timeperiod=int(rsi_period))
                                latest_rsi = float(rsi_series[-1])
                            else:
                                delta = close_series.diff()
                                gain = delta.clip(lower=0).rolling(int(rsi_period)).mean()
                                loss = (-delta.clip(upper=0)).rolling(int(rsi_period)).mean()
                                rs = gain / loss
                                latest_rsi = float((100 - (100 / (1 + rs))).iloc[-1])

                            if not np.isnan(latest_rsi):
                                rsi_passed = (latest_rsi > rsi_thresh) if ">" in rsi_cond else (latest_rsi < rsi_thresh)
                                stock_matches.append(rsi_passed)
                                info_dict[f"RSI ({int(rsi_period)})"] = round(latest_rsi, 1)
                            else:
                                stock_matches.append(False)
                        except Exception:
                            stock_matches.append(False)
                    else:
                        stock_matches.append(False)

                # MACD Filter
                if tile_macd_on:
                    if len(close_vals) >= 35:
                        try:
                            if HAS_TALIB:
                                macd_line, macd_sig, macd_hist = talib.MACD(close_vals, fastperiod=12, slowperiod=26, signalperiod=9)
                                m_val = float(macd_line[-1])
                                s_val = float(macd_sig[-1])
                                h_val = float(macd_hist[-1])
                            else:
                                ema12 = close_series.ewm(span=12, adjust=False).mean()
                                ema26 = close_series.ewm(span=26, adjust=False).mean()
                                macd_s = ema12 - ema26
                                sig_s = macd_s.ewm(span=9, adjust=False).mean()
                                hist_s = macd_s - sig_s
                                m_val = float(macd_s.iloc[-1])
                                s_val = float(sig_s.iloc[-1])
                                h_val = float(hist_s.iloc[-1])

                            if not np.isnan(m_val) and not np.isnan(s_val):
                                if "MACD > Signal" in macd_cond:
                                    macd_passed = (m_val > s_val)
                                elif "MACD < Signal" in macd_cond:
                                    macd_passed = (m_val < s_val)
                                else:
                                    macd_passed = (h_val > 0)
                                stock_matches.append(macd_passed)
                                info_dict["MACD"] = f"{m_val:.1f}/{s_val:.1f}"
                            else:
                                stock_matches.append(False)
                        except Exception:
                            stock_matches.append(False)
                    else:
                        stock_matches.append(False)

                # ADX Filter
                if tile_adx_on:
                    if len(df) >= int(adx_period) * 2:
                        try:
                            adx_vals = calculate_adx(df, period=int(adx_period))
                            latest_adx = float(adx_vals[-1])
                            if not np.isnan(latest_adx):
                                adx_passed = (latest_adx > adx_thresh) if ">" in adx_cond else (latest_adx < adx_thresh)
                                stock_matches.append(adx_passed)
                                info_dict[f"ADX ({int(adx_period)})"] = round(latest_adx, 1)
                            else:
                                stock_matches.append(False)
                        except Exception:
                            stock_matches.append(False)
                    else:
                        stock_matches.append(False)

                # % Below 52W High Filter
                if tile_52w_on:
                    if "Within" in high52_cond:
                        h52_passed = (pct_below_52w <= high52_val)
                    else:
                        h52_passed = (pct_below_52w >= high52_val)
                    stock_matches.append(h52_passed)

                # Logic match
                if stock_matches:
                    match = all(stock_matches) if "Match ALL" in filter_mode else any(stock_matches)
                    if match:
                        results.append(info_dict)

            # Results Display
            st.markdown("---")
            total_screened = len(cached_dict)
            matching_count = len(results)

            m1, m2, m3 = st.columns(3)
            m1.metric("Screened", f"{total_screened}")
            m2.metric("Matched", f"{matching_count}")
            m3.metric("Filters Active", f"{active_filters_count}")

            if results:
                res_df = pd.DataFrame(results)
                if sort_by == "Symbol":
                    res_df = res_df.sort_values(by="Symbol")
                elif sort_by == "Price":
                    res_df = res_df.sort_values(by="Price", ascending=False)
                elif sort_by == "Change (%) High to Low":
                    res_df = res_df.sort_values(by="Change %", ascending=False)
                elif sort_by == "Change (%) Low to High":
                    res_df = res_df.sort_values(by="Change %", ascending=True)
                elif sort_by == "% Below 52W High":
                    res_df = res_df.sort_values(by="% Below 52W", ascending=True)

                symbols = res_df["Symbol"].tolist()
                chips_html = "".join([f"<span class='ticker-pill'>{s}</span>" for s in symbols])
                st.markdown(f"<div style='margin-bottom: 12px;'>{chips_html}</div>", unsafe_allow_html=True)

                csv_bytes = res_df.to_csv(index=False).encode("utf-8")
                st.markdown("<div class='export-csv-wrapper'>", unsafe_allow_html=True)
                st.download_button("📥 Export CSV", csv_bytes, f"screened_{cache_tf.lower()}.csv", "text/csv")
                st.markdown("</div>", unsafe_allow_html=True)

                disp_df = res_df.copy()
                disp_df["Price"] = disp_df["Price"].apply(lambda x: f"₹{x:,.2f}")
                disp_df["Change %"] = disp_df["Change %"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.2f}%")

                st.dataframe(disp_df, width="stretch", hide_index=True)

                # Quick Inspection Chart
                selected_inspect = st.selectbox(
                    "Inspect Chart",
                    options=res_df["Ticker"].tolist(),
                    format_func=lambda x: x.replace(".NS", "").replace(".BO", "")
                )
                if selected_inspect and selected_inspect in cached_dict:
                    inspect_df = cached_dict[selected_inspect].tail(120).copy()
                    
                    if tile_adx_on:
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.75, 0.25])
                    else:
                        fig = go.Figure()

                    candlestick = go.Candlestick(
                        x=inspect_df["Date"],
                        open=inspect_df["Open"],
                        high=inspect_df["High"],
                        low=inspect_df["Low"],
                        close=inspect_df["Close"],
                        name="Price",
                        increasing_line_color="#00d09c",
                        decreasing_line_color="#eb5b3c"
                    )

                    if tile_adx_on:
                        fig.add_trace(candlestick, row=1, col=1)
                    else:
                        fig.add_trace(candlestick)

                    # Overlays
                    colors = ["#ffd166", "#06d6a0", "#118ab2", "#ef476f"]
                    for idx_m, (lbl, m_type, m_len, _) in enumerate(active_ma_specs):
                        c_ser = cached_dict[selected_inspect]["Close"].dropna()
                        m_line = c_ser.rolling(m_len).mean() if m_type == "SMA" else c_ser.ewm(span=m_len, adjust=False).mean()
                        sub_m = m_line.reindex(inspect_df.index)
                        ma_trace = go.Scatter(
                            x=inspect_df["Date"],
                            y=sub_m,
                            mode="lines",
                            name=f"{lbl} ({m_len})",
                            line=dict(color=colors[idx_m % len(colors)], width=1.5)
                        )
                        if tile_adx_on:
                            fig.add_trace(ma_trace, row=1, col=1)
                        else:
                            fig.add_trace(ma_trace)

                    if tile_st_on:
                        try:
                            full_st, _ = calculate_supertrend(cached_dict[selected_inspect], period=int(st_period), multiplier=float(st_multiplier))
                            sub_st = pd.Series(full_st, index=cached_dict[selected_inspect].index).reindex(inspect_df.index)
                            st_trace = go.Scatter(
                                x=inspect_df["Date"],
                                y=sub_st,
                                mode="lines",
                                name="Supertrend",
                                line=dict(color="#00d09c", width=1.5, dash="dot")
                            )
                            if tile_adx_on:
                                fig.add_trace(st_trace, row=1, col=1)
                            else:
                                fig.add_trace(st_trace)
                        except Exception:
                            pass

                    # ADX Subplot
                    if tile_adx_on:
                        full_adx = calculate_adx(cached_dict[selected_inspect], period=int(adx_period))
                        sub_adx = pd.Series(full_adx, index=cached_dict[selected_inspect].index).reindex(inspect_df.index)
                        fig.add_trace(go.Scatter(
                            x=inspect_df["Date"],
                            y=sub_adx,
                            mode="lines",
                            name=f"ADX ({int(adx_period)})",
                            line=dict(color="#a78bfa", width=1.5)
                        ), row=2, col=1)
                        fig.add_hline(y=adx_thresh, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=2, col=1)

                    fig.update_layout(
                        template="plotly_dark",
                        height=460 if not tile_adx_on else 520,
                        margin=dict(l=15, r=15, t=15, b=15),
                        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", rangeslider=dict(visible=False)),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                        hovermode="x unified",
                        plot_bgcolor="#121721",
                        paper_bgcolor="#121721"
                    )
                    if tile_adx_on:
                        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", row=2, col=1)

                    st.plotly_chart(fig, width="stretch")
            else:
                st.info("No matching stocks.")


# ---------------------------------------------------------
# STOCK DATA PAGE
# ---------------------------------------------------------
elif st.session_state.current_page == "Download Stock Data":
    top_c1, top_c2 = st.columns([1, 6])
    with top_c1:
        if st.button("← Back", key="dl_back"):
            st.session_state.current_page = "Home"
            st.rerun()
    with top_c2:
        st.markdown("<h2 class='gradient-header-text'>Stock Data & Charts</h2>", unsafe_allow_html=True)

    tab_single, tab_batch = st.tabs(["Single Stock Analysis", "Batch Download (CSV Upload)"])

    with tab_single:
        # Inputs bar
        with st.container():
            c_ex, c_tk, c_from, c_to, c_tf = st.columns([1.2, 1.8, 1.2, 1.2, 1.1])
            with c_ex:
                exchange = st.selectbox("Exchange", ["NSE", "BSE", "US / Global"], index=0, key="single_ex")
            
            if exchange == "NSE":
                exchange_suffix = ".NS"
                currency_symbol = "₹"
            elif exchange == "BSE":
                exchange_suffix = ".BO"
                currency_symbol = "₹"
            else:
                exchange_suffix = ""
                currency_symbol = "$"

            with c_tk:
                stock_opts = [f"{sym} ({name})" for sym, name in POPULAR_NSE_STOCKS.items()] + ["Custom..."]
                selected_option = st.selectbox("Stock", stock_opts, index=0, key="single_stock_sel")
                if selected_option == "Custom...":
                    raw_ticker = st.text_input("Ticker", value="RELIANCE", key="single_custom_tick").strip().upper()
                else:
                    raw_ticker = selected_option.split(" (")[0].strip()

                def format_ticker(t: str, sfx: str) -> str:
                    t = t.strip().upper()
                    if not t:
                        return ""
                    if sfx:
                        if not t.endswith(sfx):
                            if "." in t:
                                return f"{t.split('.')[0]}{sfx}"
                            return f"{t}{sfx}"
                        return t
                    else:
                        if t.endswith(".NS") or t.endswith(".BO"):
                            return t.split(".")[0]
                        return t

                final_ticker = format_ticker(raw_ticker, exchange_suffix)

            today = date.today()
            default_start = today - timedelta(days=365)
            with c_from:
                start_date = st.date_input("From", value=default_start, max_value=today, key="single_from")
            with c_to:
                end_date = st.date_input("To", value=today, min_value=start_date, max_value=today, key="single_to")
            with c_tf:
                timeframe_choice = st.selectbox("Timeframe", ["Daily", "Weekly", "Monthly"], index=0, key="single_tf")
                tf_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
                selected_interval = tf_map[timeframe_choice]

            if st.button("Fetch Data", type="primary", key="btn_single_fetch"):
                if final_ticker and start_date <= end_date:
                    with st.spinner("Loading..."):
                        try:
                            data = load_stock_data(final_ticker, start_date, end_date, selected_interval)
                            if data is None or data.empty:
                                st.error(f"No data found for {final_ticker}")
                                st.session_state.stock_data = None
                                st.session_state.query_info = None
                            else:
                                st.session_state.stock_data = data
                                st.session_state.query_info = {
                                    "ticker": final_ticker,
                                    "raw_ticker": raw_ticker,
                                    "start_date": start_date,
                                    "end_date": end_date,
                                    "timeframe": timeframe_choice,
                                    "currency": currency_symbol
                                }
                        except Exception as e:
                            st.error(f"Error: {e}")

    with tab_batch:
        st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 12px;'>Upload a CSV file with stock tickers to fetch historical OHLCV data in batch and download them packaged together into a single <b>ZIP file</b> containing individual CSV files.</p>", unsafe_allow_html=True)
        
        batch_col1, batch_col2 = st.columns([2, 1])
        with batch_col1:
            batch_csv_file = st.file_uploader("Upload CSV containing stock tickers", type=["csv"], key="batch_stock_csv")
        with batch_col2:
            batch_exchange = st.selectbox("Exchange Suffix", ["NSE (.NS)", "BSE (.BO)", "US / None"], index=0, key="batch_exchange")

        batch_from_col, batch_to_col, batch_tf_col = st.columns(3)
        today_b = date.today()
        with batch_from_col:
            batch_start = st.date_input("From Date", value=today_b - timedelta(days=365), max_value=today_b, key="batch_from_date")
        with batch_to_col:
            batch_end = st.date_input("To Date", value=today_b, min_value=batch_start, max_value=today_b, key="batch_to_date")
        with batch_tf_col:
            batch_tf = st.selectbox("Timeframe", ["Daily", "Weekly", "Monthly"], index=0, key="batch_tf_choice")
            batch_interval = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}[batch_tf]

        parsed_batch_tickers = []
        if batch_csv_file is not None:
            try:
                batch_csv_file.seek(0)
                b_df = pd.read_csv(batch_csv_file)
                found_b_col = None
                for col_name in ["symbol", "ticker", "stock", "symbols", "tickers", "stocks", "name", "tradingsymbol"]:
                    for actual_col in b_df.columns:
                        if str(actual_col).strip().lower() == col_name:
                            found_b_col = actual_col
                            break
                    if found_b_col:
                        break
                if found_b_col is None:
                    found_b_col = b_df.columns[0]

                raw_parsed = (
                    b_df[found_b_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .tolist()
                )
                parsed_batch_tickers = [t for t in raw_parsed if t and t not in ["SYMBOL", "TICKER", "STOCK", "NAME"]]
                if parsed_batch_tickers:
                    st.caption(f"✓ Found **{len(parsed_batch_tickers)} tickers** in `{batch_csv_file.name}`")
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        # Quick sample button option
        if not parsed_batch_tickers:
            if st.button("🚀 Load 30 Benchmark Nifty Stocks for Batch", key="btn_load_batch_sample"):
                parsed_batch_tickers = [
                    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
                    "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "MARUTI", "BAJFINANCE",
                    "AXISBANK", "SUNPHARMA", "TITAN", "KOTAKBANK", "ULTRACEMCO", "WIPRO",
                    "NTPC", "POWERGRID", "HINDUNILVR", "JSWSTEEL", "TATASTEEL", "ADANIENT",
                    "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "NESTLEIND", "ONGC", "M&M"
                ]
                st.session_state["batch_sample_active"] = True

        if st.session_state.get("batch_sample_active", False) and not parsed_batch_tickers:
            parsed_batch_tickers = [
                "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN",
                "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "MARUTI", "BAJFINANCE",
                "AXISBANK", "SUNPHARMA", "TITAN", "KOTAKBANK", "ULTRACEMCO", "WIPRO",
                "NTPC", "POWERGRID", "HINDUNILVR", "JSWSTEEL", "TATASTEEL", "ADANIENT",
                "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "NESTLEIND", "ONGC", "M&M"
            ]

        def format_batch_symbol(tick: str, ex_setting: str) -> str:
            tick = tick.strip().upper()
            if "NSE" in ex_setting and not tick.endswith(".NS"):
                return f"{tick.split('.')[0]}.NS"
            elif "BSE" in ex_setting and not tick.endswith(".BO"):
                return f"{tick.split('.')[0]}.BO"
            return tick

        if parsed_batch_tickers:
            unique_batch_symbols = list(dict.fromkeys([format_batch_symbol(t, batch_exchange) for t in parsed_batch_tickers]))
            st.info(f"Ready to download **{len(unique_batch_symbols)} tickers** ({batch_tf} interval, from {batch_start} to {batch_end})")
            
            if st.button("📦 Start Batch Download & Create ZIP", type="primary", key="btn_start_batch_zip"):
                zip_buffer = io.BytesIO()
                success_count = 0
                failed_symbols = []
                batch_prog = st.progress(0, text="Fetching batch data...")

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for idx, sym in enumerate(unique_batch_symbols):
                        batch_prog.progress(
                            int(((idx + 1) / len(unique_batch_symbols)) * 100),
                            text=f"Downloading {sym} ({idx+1}/{len(unique_batch_symbols)})..."
                        )
                        clean_fn = sym.replace(".NS", "").replace(".BO", "")
                        try:
                            s_data = load_stock_data(sym, batch_start, batch_end, batch_interval)
                            if s_data is not None and not s_data.empty:
                                csv_str = s_data.to_csv(index=False)
                                zf.writestr(f"{clean_fn}_{batch_tf.lower()}.csv", csv_str)
                                success_count += 1
                            else:
                                failed_symbols.append(sym)
                        except Exception:
                            failed_symbols.append(sym)

                batch_prog.empty()
                if success_count > 0:
                    zip_buffer.seek(0)
                    zip_bytes = zip_buffer.getvalue()
                    st.success(f"Successfully packaged **{success_count} stocks** into ZIP archive!")
                    st.download_button(
                        label=f"💾 Download {success_count} Stocks ZIP",
                        data=zip_bytes,
                        file_name=f"stocks_batch_{batch_tf.lower()}_{date.today().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        type="primary"
                    )
                if failed_symbols:
                    st.warning(f"Could not retrieve data for {len(failed_symbols)} tickers: {', '.join(failed_symbols[:10])}")

    # Results Display
    if st.session_state.stock_data is not None and st.session_state.query_info is not None:
        df = st.session_state.stock_data
        info = st.session_state.query_info
        curr = info["currency"]

        first_close = float(df.iloc[0]["Close"])
        last_close = float(df.iloc[-1]["Close"])
        pts_change = last_close - first_close
        pct_change = (pts_change / first_close) * 100 if first_close != 0 else 0
        p_high = float(df["High"].max())
        p_low = float(df["Low"].min())

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            label=f"{info['raw_ticker']} Price",
            value=f"{curr}{last_close:,.2f}",
            delta=f"{'+' if pts_change >= 0 else ''}{curr}{abs(pts_change):,.2f} ({'+' if pct_change >= 0 else ''}{pct_change:.2f}%)"
        )
        m2.metric(label="Open", value=f"{curr}{first_close:,.2f}")
        m3.metric(label="High", value=f"{curr}{p_high:,.2f}")
        m4.metric(label="Low", value=f"{curr}{p_low:,.2f}")

        # Chart controls
        ch_c1, ch_c2 = st.columns([4, 1])
        with ch_c2:
            chart_type = st.radio("Chart", ["Line", "Candle"], horizontal=True, label_visibility="collapsed")

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.75, 0.25])
        
        is_positive = pts_change >= 0
        primary_color = "#00d09c" if is_positive else "#eb5b3c"
        fill_color = "rgba(0, 208, 156, 0.12)" if is_positive else "rgba(235, 91, 60, 0.12)"

        if chart_type == "Line":
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=df["Close"],
                mode="lines",
                name="Close",
                line=dict(color=primary_color, width=2),
                fill="tozeroy",
                fillcolor=fill_color
            ), row=1, col=1)
        else:
            fig.add_trace(go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
                increasing_line_color="#00d09c",
                decreasing_line_color="#eb5b3c"
            ), row=1, col=1)

        if "Volume" in df.columns:
            vol_colors = ["#00d09c" if c >= o else "#eb5b3c" for c, o in zip(df["Close"], df["Open"])]
            fig.add_trace(go.Bar(
                x=df["Date"],
                y=df["Volume"],
                name="Volume",
                marker_color=vol_colors,
                opacity=0.6
            ), row=2, col=1)

        fig.update_layout(
            template="plotly_dark",
            height=460,
            margin=dict(l=15, r=15, t=15, b=15),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            xaxis2=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            yaxis2=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            hovermode="x unified",
            showlegend=False,
            plot_bgcolor="#121721",
            paper_bgcolor="#121721"
        )
        st.plotly_chart(fig, width="stretch")

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export CSV",
            csv_bytes,
            f"{info['ticker']}_{info['timeframe'].lower()}.csv",
            "text/csv"
        )

        display_df = df.copy()
        if "Date" in display_df.columns:
            display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        for col in ["Open", "High", "Low", "Close"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{curr}{x:,.2f}" if pd.notnull(x) else "")
        if "Volume" in display_df.columns:
            display_df["Volume"] = display_df["Volume"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")

        st.dataframe(display_df, width="stretch", height=300, hide_index=True)