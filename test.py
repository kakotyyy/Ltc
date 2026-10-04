import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Stock Data & Screen",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Styling (Modern & Sleek FinTech UI)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Metric card styling */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 14px 18px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 150, 255, 0.5);
    }
    
    /* Exchange badge */
    .badge-exchange {
        background: #0070f3;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    .status-positive {
        color: #00C805;
        font-weight: 700;
    }
    
    .status-negative {
        color: #FF3B30;
        font-weight: 700;
    }
    
    /* Mode navigation cards */
    .mode-card {
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
        background: rgba(255, 255, 255, 0.03);
        transition: all 0.25s ease;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .mode-card:hover {
        border-color: #0070f3;
        background: rgba(0, 112, 243, 0.05);
        transform: translateY(-3px);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Popular NSE Stocks Directory (15 major NSE stocks)
# ---------------------------------------------------------
POPULAR_NSE_STOCKS = {
    "RELIANCE": "Reliance Industries Ltd.",
    "TCS": "Tata Consultancy Services Ltd.",
    "HDFCBANK": "HDFC Bank Ltd.",
    "INFY": "Infosys Ltd.",
    "ICICIBANK": "ICICI Bank Ltd.",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel Ltd.",
    "ITC": "ITC Ltd.",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd.",
    "LT": "Larsen & Toubro Ltd.",
    "TATAMOTORS": "Tata Motors Ltd.",
    "HINDUNILVR": "Hindustan Unilever Ltd.",
    "BAJFINANCE": "Bajaj Finance Ltd.",
    "MARUTI": "Maruti Suzuki India Ltd.",
    "WIPRO": "Wipro Ltd."
}

# ---------------------------------------------------------
# Navigation & Session State
# ---------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if "stock_data" not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.query_info = None

# Custom CSS for Modern Dark FinTech UI (Inspired by Luxury Landing Design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Top Pill Navigation Bar */
    .top-navbar-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        margin-bottom: 30px;
        background: rgba(18, 19, 26, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 50px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .brand-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .brand-icon {
        background: linear-gradient(135deg, #0070f3, #00dfd8);
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        color: white;
    }
    .nav-pill-group {
        display: flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.05);
        padding: 4px;
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        gap: 6px;
    }
    .nav-pill-item {
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #a0aec0;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    .nav-pill-item.active {
        background: #ffffff;
        color: #0b0c10;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    .nav-pill-item:hover:not(.active) {
        color: #ffffff;
    }
    .status-chip {
        background: rgba(0, 223, 216, 0.12);
        color: #00dfd8;
        border: 1px solid rgba(0, 223, 216, 0.25);
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    /* Hero Center Section */
    .hero-container {
        text-align: center;
        max-width: 860px;
        margin: 20px auto 40px auto;
        padding: 0 15px;
    }
    .hero-announcement {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 6px 18px;
        border-radius: 30px;
        font-size: 0.84rem;
        color: #cbd5e1;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .hero-announcement span.sparkle {
        color: #38bdf8;
    }
    .hero-title {
        font-size: 3.4rem;
        font-weight: 800;
        letter-spacing: -1.2px;
        line-height: 1.15;
        margin-bottom: 12px;
        color: #ffffff;
        background: linear-gradient(180deg, #ffffff 60%, rgba(255, 255, 255, 0.7) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.65rem;
        font-weight: 500;
        color: #94a3b8;
        letter-spacing: -0.4px;
        margin-bottom: 16px;
    }
    .hero-desc {
        font-size: 0.98rem;
        color: #64748b;
        max-width: 620px;
        margin: 0 auto 30px auto;
        line-height: 1.6;
    }

    /* Card Box Visuals */
    .feature-card-wrapper {
        position: relative;
        border-radius: 24px;
        padding: 2px;
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.02) 40%, rgba(0, 112, 243, 0.2));
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
    }
    .feature-card-wrapper:hover {
        transform: translateY(-6px);
        box-shadow: 0 25px 50px -10px rgba(0, 112, 243, 0.3);
    }
    .feature-card-inner {
        background: radial-gradient(circle at top left, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.9) 70%);
        backdrop-filter: blur(20px);
        border-radius: 22px;
        padding: 34px 28px 24px 28px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 250px;
    }
    .card-glow-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        width: fit-content;
        margin-bottom: 18px;
    }
    .glow-blue {
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(14, 165, 233, 0.3);
    }
    .glow-purple {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    .card-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
        letter-spacing: -0.4px;
    }
    .card-desc {
        font-size: 0.88rem;
        color: #94a3b8;
        line-height: 1.5;
        margin-bottom: 24px;
    }
    .card-chip-badge {
        font-family: 'Courier New', monospace;
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.05);
        padding: 4px 10px;
        border-radius: 6px;
        color: #cbd5e1;
        display: inline-block;
    }

    /* Entire Clickable Card Button Styling */
    div.st-key-btn_download button,
    div.st-key-btn_screener button {
        height: 200px !important;
        min-height: 200px !important;
        padding: 24px !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        background: radial-gradient(circle at top left, rgba(30, 41, 59, 0.65), rgba(15, 23, 42, 0.95) 75%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        cursor: pointer !important;
    }
    
    div.st-key-btn_download button:hover {
        border-color: rgba(56, 189, 248, 0.7) !important;
        transform: translateY(-5px) !important;
        box-shadow: 0 25px 50px -10px rgba(14, 165, 233, 0.35) !important;
    }

    div.st-key-btn_screener button:hover {
        border-color: rgba(192, 132, 252, 0.7) !important;
        transform: translateY(-5px) !important;
        box-shadow: 0 25px 50px -10px rgba(168, 85, 247, 0.35) !important;
    }

    div.st-key-btn_download button p,
    div.st-key-btn_screener button p {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: -0.5px !important;
        text-align: center !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper function to fetch & process data
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=300)
def load_stock_data(ticker: str, start: date, end: date, interval: str):
    """
    Downloads historical stock data from yfinance and flattens column multi-index if present.
    yfinance end date is exclusive, so add 1 day to include the user selected end_date.
    """
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
    
    # Flatten MultiIndex columns if returned by newer yfinance versions
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    
    # Reset index so 'Date' is a regular column
    df = df.reset_index()
    
    # Ensure Date column is formatted nicely
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    elif "Datetime" in df.columns:
        df.rename(columns={"Datetime": "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        
    return df

# ---------------------------------------------------------
# Screen Routing
# ---------------------------------------------------------
if st.session_state.current_page == "Home":
    # 1. Top Pill Navigation Bar
    st.markdown("""
    <div class="top-navbar-container">
        <div class="brand-logo">
            <div class="brand-icon">📈</div>
            <span>StockPulse</span>
        </div>
        <div class="nav-pill-group">
            <span class="nav-pill-item active">Home</span>
            <span class="nav-pill-item">Data Hub</span>
            <span class="nav-pill-item">Screener</span>
            <span class="nav-pill-item">Analytics</span>
        </div>
        <div>
            <span class="status-chip">⚡ Live Markets</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Hero Center Section with Main Heading
    st.markdown("""
    <div class="hero-container">
        <div class="hero-announcement">
            <span class="sparkle">✦</span>
            <span>Real-time NSE, BSE & Global Market Feeds</span>
            <span style="color:#0070f3; font-weight:700;">→</span>
        </div>
        <h1 class="hero-title">Stock Data & Screen</h1>
        <div class="hero-subtitle">OHLC Data Downloader & Technical Screener</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Two Luxury Interactive Cards (Download Stock Data & Screener)
    col_card1, col_card2 = st.columns(2, gap="large")
    with col_card1:
        if st.button("Download Stock Data", key="btn_download", use_container_width=True):
            st.session_state.current_page = "Download Stock Data"
            st.rerun()
            
    with col_card2:
        if st.button("Screener", key="btn_screener", use_container_width=True):
            st.session_state.current_page = "Screener"
            st.rerun()

elif st.session_state.current_page == "Screener":
    st.sidebar.button("🏠 Back to Home", on_click=lambda: st.session_state.update(current_page="Home"))
    st.title("Stock Data & Screen")
    st.markdown("### 🔍 Screener")
    st.info("🚧 Screener feature is coming soon! We will code this section next.")
    if st.button("← Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()

elif st.session_state.current_page == "Download Stock Data":
    st.sidebar.button("🏠 Back to Home", on_click=lambda: st.session_state.update(current_page="Home"))
    
    # ---------------------------------------------------------
    # Sidebar Controls & Parameters (Download Stock Data)
    # ---------------------------------------------------------
    st.sidebar.markdown("## ⚙️ Configuration")
    st.sidebar.markdown("Customize your stock query parameters below.")
    
    # 1. Exchange Selection
    exchange = st.sidebar.selectbox(
        "Select Stock Exchange",
        options=["NSE (National Stock Exchange - India)", "BSE (Bombay Stock Exchange - India)", "US / Global (NYSE, NASDAQ)"],
        index=0,
        help="When NSE is selected, '.NS' will automatically be appended to format the ticker for yfinance."
    )
    
    # Determine ticker suffix and currency symbol based on exchange
    if "NSE" in exchange:
        exchange_suffix = ".NS"
        currency_symbol = "₹"
        exchange_name = "NSE"
    elif "BSE" in exchange:
        exchange_suffix = ".BO"
        currency_symbol = "₹"
        exchange_name = "BSE"
    else:
        exchange_suffix = ""
        currency_symbol = "$"
        exchange_name = "GLOBAL"
        
    # 2. Stock Ticker Selection (Dropdown with 10+ NSE stocks + Custom option)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏷️ Stock Selection")
    
    stock_options = [f"{sym} ({name})" for sym, name in POPULAR_NSE_STOCKS.items()] + ["➕ Enter Custom Ticker..."]
    selected_option = st.sidebar.selectbox(
        "Choose Stock (10+ Popular NSE Stocks)",
        stock_options,
        index=0,
        help="Select one of the top NSE stocks or choose 'Enter Custom Ticker' to type any stock symbol."
    )
    
    if selected_option == "➕ Enter Custom Ticker...":
        raw_ticker = st.sidebar.text_input(
            "Enter Custom Ticker Symbol",
            value="RELIANCE",
            help="Type ticker symbol. For NSE, you can type RELIANCE or RELIANCE.NS"
        ).strip().upper()
    else:
        raw_ticker = selected_option.split(" (")[0].strip()
        
    def format_ticker(ticker: str, suffix: str) -> str:
        ticker = ticker.strip().upper()
        if not ticker:
            return ""
        if suffix:
            if not ticker.endswith(suffix):
                if "." in ticker:
                    base_part = ticker.split(".")[0]
                    return f"{base_part}{suffix}"
                return f"{ticker}{suffix}"
            return ticker
        else:
            if ticker.endswith(".NS") or ticker.endswith(".BO"):
                return ticker.split(".")[0]
            return ticker
            
    final_ticker = format_ticker(raw_ticker, exchange_suffix)
    st.sidebar.info(f"📌 **Formatted yfinance Ticker:** `{final_ticker}`")
    
    # 3. Date Range Selection
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Date & Period")
    
    today = date.today()
    default_start = today - timedelta(days=365)
    
    col_date1, col_date2 = st.sidebar.columns(2)
    with col_date1:
        start_date = st.date_input("From Date", value=default_start, max_value=today)
    with col_date2:
        end_date = st.date_input("To Date", value=today, min_value=start_date, max_value=today)
        
    # 4. Timeframe
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⏱️ Timeframe")
    timeframe_choice = st.sidebar.selectbox(
        "Select Timeframe",
        options=["Daily", "Weekly", "Monthly"],
        index=0
    )
    
    timeframe_map = {
        "Daily": "1d",
        "Weekly": "1wk",
        "Monthly": "1mo"
    }
    selected_interval = timeframe_map[timeframe_choice]
    
    # 5. Fetch Button
    st.sidebar.markdown("---")
    fetch_button = st.sidebar.button("🚀 Fetch Stock Data", type="primary", use_container_width=True)
    
    # Page Header
    st.title("Stock Data & Screen")
    st.markdown(
        f"OHCL data downloader & Basic Technical Screener. "
        f"<span class='badge-exchange'>{exchange_name}</span>",
        unsafe_allow_html=True
    )
    
    # If user clicked Fetch, perform fetch
    if fetch_button:
        if not final_ticker:
            st.error("⚠️ Please specify a valid ticker symbol.")
        elif start_date > end_date:
            st.error("⚠️ 'From Date' cannot be after 'To Date'.")
        else:
            with st.spinner(f"Fetching data for {final_ticker} ({timeframe_choice})..."):
                try:
                    data = load_stock_data(final_ticker, start_date, end_date, selected_interval)
                    if data is None or data.empty:
                        st.error(f"❌ No data found for ticker '{final_ticker}' between {start_date} and {end_date}. "
                                 f"Please verify the ticker symbol and selected exchange.")
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
                    st.error(f"❌ An error occurred while fetching data: {str(e)}")
                    st.session_state.stock_data = None
                    st.session_state.query_info = None

    # ---------------------------------------------------------
    # Render Results when Data is Available
    # ---------------------------------------------------------
    if st.session_state.stock_data is not None and st.session_state.query_info is not None:
        df = st.session_state.stock_data
        info = st.session_state.query_info
        curr = info["currency"]
        
        # Summary Bar
        st.markdown(f"### Performance Summary for `{info['ticker']}` ({info['timeframe']})")
        st.caption(f"📅 Period: **{info['start_date']}** to **{info['end_date']}** | 📊 Total Candles/Bars: **{len(df)}**")
        
        # Calculate performance metrics
        first_row = df.iloc[0]
        last_row = df.iloc[-1]
        
        # Initial & Final price calculation
        initial_close = float(first_row["Close"])
        final_close = float(last_row["Close"])
        
        points_change = final_close - initial_close
        pct_change = (points_change / initial_close) * 100 if initial_close != 0 else 0
        
        period_high = float(df["High"].max())
        period_low = float(df["Low"].min())
        total_volume = int(df["Volume"].sum()) if "Volume" in df.columns else 0
        
        sign = "+" if points_change >= 0 else "-"
        abs_points = abs(points_change)
        delta_str = f"{sign}{curr} {abs_points:,.2f} ({sign}{abs(pct_change):.2f}%)"
        
        # Display Key Metrics in 5 clean columns
        m1, m2, m3, m4, m5 = st.columns(5)
        
        m1.metric(
            label="Closing Price",
            value=f"{curr} {final_close:,.2f}",
            delta=delta_str
        )
        
        m2.metric(
            label="Points Gained / Lost",
            value=f"{sign}{curr} {abs_points:,.2f}",
            delta=f"{sign}{abs(pct_change):.2f}%"
        )
        
        m3.metric(
            label="Percentage Change (%)",
            value=f"{sign}{abs(pct_change):.2f}%",
            delta=f"{sign}{abs_points:,.2f} pts"
        )
        
        m4.metric(
            label="Starting Price (Close)",
            value=f"{curr} {initial_close:,.2f}"
        )
        
        m5.metric(
            label="Period Range (Low - High)",
            value=f"{curr} {period_low:,.2f} - {curr} {period_high:,.2f}"
        )
        
        st.markdown("---")
        
        # ---------------------------------------------------------
        # Interactive Chart Section
        # ---------------------------------------------------------
        col_chart_header, col_chart_opts, col_ma_opts = st.columns([2, 1, 1])
        with col_chart_header:
            st.subheader("📊 Interactive Price Chart")
        with col_chart_opts:
            chart_type = st.radio("Chart Type", ["Line Chart", "Candlestick"], horizontal=True)
        with col_ma_opts:
            show_ma = st.checkbox("Show 20-period SMA", value=False)
        
        # Plotly Figure with Subplots (Price on top, Volume at bottom)
        from plotly.subplots import make_subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.75, 0.25],
            subplot_titles=("Price Action", "Volume")
        )
        
        line_color = "#00C805" if points_change >= 0 else "#FF3B30"
        fill_color = "rgba(0, 200, 5, 0.12)" if points_change >= 0 else "rgba(255, 59, 48, 0.12)"
        
        if chart_type == "Line Chart":
            # Interactive Close price line with area fill
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=df["Close"],
                mode="lines",
                name="Close Price",
                line=dict(color=line_color, width=2.5),
                fill="tozeroy",
                fillcolor=fill_color,
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Close:</b> " + curr + " %{y:,.2f}<extra></extra>"
            ), row=1, col=1)
        else:
            # Candlestick chart
            fig.add_trace(go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
                increasing_line_color="#00C805",
                decreasing_line_color="#FF3B30",
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br>" +
                              "<b>Open:</b> " + curr + " %{open:,.2f}<br>" +
                              "<b>High:</b> " + curr + " %{high:,.2f}<br>" +
                              "<b>Low:</b> " + curr + " %{low:,.2f}<br>" +
                              "<b>Close:</b> " + curr + " %{close:,.2f}<extra></extra>"
            ), row=1, col=1)
            
        # Moving Average option
        if show_ma and len(df) >= 20:
            sma_20 = df["Close"].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=sma_20,
                mode="lines",
                name="20 SMA",
                line=dict(color="#FF9500", width=1.8, dash="dot"),
                hovertemplate="<b>20 SMA:</b> " + curr + " %{y:,.2f}<extra></extra>"
            ), row=1, col=1)
            
        # Volume bars
        if "Volume" in df.columns:
            vol_colors = ["#00C805" if c >= o else "#FF3B30" for c, o in zip(df["Close"], df["Open"])]
            fig.add_trace(go.Bar(
                x=df["Date"],
                y=df["Volume"],
                name="Volume",
                marker_color=vol_colors,
                opacity=0.6,
                hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Volume:</b> %{y:,}<extra></extra>"
            ), row=2, col=1)
            
        fig.update_layout(
            template="plotly_dark",
            height=540,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
            xaxis2=dict(title="Date", showgrid=True, gridcolor="rgba(128,128,128,0.15)", rangeslider=dict(visible=False)),
            yaxis=dict(title=f"Price ({curr})", showgrid=True, gridcolor="rgba(128,128,128,0.15)", tickformat=",.2f"),
            yaxis2=dict(title="Volume", showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ---------------------------------------------------------
        # Data Table & CSV Download Section
        # ---------------------------------------------------------
        st.markdown("---")
        col_table_header, col_download = st.columns([3, 1])
        
        with col_table_header:
            st.subheader("📋 Historical Stock Data Table")
            
        # Prepare CSV export
        csv_data = df.to_csv(index=False).encode("utf-8")
        filename = f"{info['ticker']}_{info['start_date']}_to_{info['end_date']}_{info['timeframe'].lower()}.csv"
        
        with col_download:
            st.download_button(
                label="📥 Download Data (.CSV)",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
            
        # Format dataframe for display
        display_df = df.copy()
        if "Date" in display_df.columns:
            display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
            
        # Format price columns nicely
        price_cols = [col for col in ["Open", "High", "Low", "Close", "Adj Close"] if col in display_df.columns]
        for col in price_cols:
            display_df[col] = display_df[col].apply(lambda x: f"{curr} {x:,.2f}" if pd.notnull(x) else "")
            
        if "Volume" in display_df.columns:
            display_df["Volume"] = display_df["Volume"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")
            
        st.dataframe(
            display_df,
            use_container_width=True,
            height=350,
            hide_index=True
        )

    else:
        # Welcome / Instructions view before clicking Fetch
        st.info("👈 Select your stock ticker, date range, and timeframe in the sidebar, then click **'🚀 Fetch Stock Data'** to view analytics.")