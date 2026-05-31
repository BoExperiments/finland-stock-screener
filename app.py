"""Finland Stock Screener — Nasdaq Helsinki (OMX)"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from tickers import HELSINKI_STOCKS, DEFAULT_WATCHLIST
from data import fetch_snapshot, fetch_intraday, fetch_daily
from signals import add_indicators, generate_signals, rsi_label, last_signal
from charts import build_main_chart

st.set_page_config(
    page_title="Finland Stock Screener",
    page_icon="🇫🇮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────
if "chart_ticker" not in st.session_state:
    st.session_state["chart_ticker"] = "NOKIA.HE"
if "switch_to_chart" not in st.session_state:
    st.session_state["switch_to_chart"] = False

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🇫🇮 Finland Stocks")
    st.caption("Nasdaq Helsinki · Yahoo Finance")

    st.divider()
    st.subheader("Screener Filters")

    min_change = st.slider("Min Change %", -15.0, 0.0, -5.0, 0.5)
    max_change = st.slider("Max Change %", 0.0, 15.0, 10.0, 0.5)
    min_vol_ratio = st.slider("Min Volume / 20d Avg", 0.0, 5.0, 0.5, 0.1,
                               help="1.0 = average volume, 2.0 = double average")
    rsi_min, rsi_max = st.slider("RSI Range", 0, 100, (20, 80))

    use_default = st.checkbox("Liquid large-caps only", value=True,
                               help="Uncheck to scan all listed Helsinki stocks")

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

# ── Auto-switch tab via JS when a stock is clicked in the screener ────────────
def inject_tab_switch():
    """Inject JS to programmatically click the Chart & Signals tab."""
    components.html("""
    <script>
        // Walk up to the Streamlit parent document and click the second tab
        function switchTab() {
            const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs.length >= 2) {
                tabs[1].click();
            }
        }
        // Small delay to let Streamlit finish rendering
        setTimeout(switchTab, 120);
    </script>
    """, height=0)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📋 Screener", "📈 Chart & Signals"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCREENER
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Stock Screener — Nasdaq Helsinki")
    st.caption("Click any row to open its chart in the **Chart & Signals** tab.")

    ticker_pool = DEFAULT_WATCHLIST if use_default else list(HELSINKI_STOCKS.keys())

    with st.spinner(f"Fetching data for {len(ticker_pool)} stocks…"):
        df_screen = fetch_snapshot(ticker_pool)

    if df_screen.empty:
        st.warning("No data returned. Markets may be closed or tickers unavailable.")
        st.stop()

    # ── Compute RSI for screener ──────────────────────────────────────────────
    rsi_values = {}
    for tkr in df_screen["Ticker"].tolist():
        try:
            hist = fetch_daily(tkr, period="3mo")
            hist = add_indicators(hist)
            if "RSI" in hist.columns and not hist["RSI"].empty:
                rsi_values[tkr] = round(hist["RSI"].dropna().iloc[-1], 1)
        except Exception:
            rsi_values[tkr] = None

    df_screen["RSI"] = df_screen["Ticker"].map(rsi_values)

    # ── Apply filters ─────────────────────────────────────────────────────────
    mask = (
        (df_screen["Change %"] >= min_change) &
        (df_screen["Change %"] <= max_change) &
        (df_screen["Vol/Avg"] >= min_vol_ratio)
    )
    if rsi_values:
        rsi_mask = df_screen["RSI"].between(rsi_min, rsi_max, inclusive="both")
        mask = mask & (rsi_mask | df_screen["RSI"].isna())

    df_filtered = df_screen[mask].copy()
    df_filtered["Company"] = df_filtered["Ticker"].map(HELSINKI_STOCKS).fillna(df_filtered["Ticker"])

    # ── Metrics bar ───────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Stocks scanned", len(df_screen))
    col_b.metric("Passed filters", len(df_filtered))
    col_c.metric("Filters active", sum([
        min_change != -5.0, max_change != 10.0,
        min_vol_ratio != 0.5, rsi_min != 20 or rsi_max != 80,
    ]))

    st.divider()

    if df_filtered.empty:
        st.info("No stocks match current filters. Try relaxing the criteria.")
    else:
        display_cols = ["Ticker", "Company", "Price", "Change %", "Vol/Avg", "RSI"]
        display_df = (
            df_filtered[display_cols]
            .sort_values("Change %", ascending=False)
            .reset_index(drop=True)
        )

        def colour_change(val):
            color = "#26a69a" if val >= 0 else "#ef5350"
            return f"color: {color}; font-weight: bold"

        def colour_rsi(val):
            if pd.isna(val):
                return ""
            if val >= 70:
                return "color: #ef5350"
            if val <= 30:
                return "color: #26a69a"
            return ""

        style_fn = "map" if hasattr(display_df.style, "map") else "applymap"
        styled = display_df.style
        styled = getattr(styled, style_fn)(colour_change, subset=["Change %"])
        styled = getattr(styled, style_fn)(colour_rsi, subset=["RSI"])
        styled = styled.format({
            "Price": "{:.2f}",
            "Change %": "{:+.2f}%",
            "Vol/Avg": "{:.2f}x",
            "RSI": "{:.1f}",
        })

        # ── Clickable dataframe — single-row selection ────────────────────────
        event = st.dataframe(
            styled,
            use_container_width=True,
            height=460,
            on_select="rerun",
            selection_mode="single-row",
        )

        selected_rows = event.selection.get("rows", []) if event and event.selection else []

        if selected_rows:
            row_idx = selected_rows[0]
            clicked_ticker = display_df.iloc[row_idx]["Ticker"]
            clicked_company = display_df.iloc[row_idx]["Company"]

            # Store in session state and flag the tab switch
            st.session_state["chart_ticker"] = clicked_ticker
            st.session_state["switch_to_chart"] = True

            st.success(f"**{clicked_ticker}** — {clicked_company} selected. Switching to Chart tab…")
            inject_tab_switch()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CHART & SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    # Clear the switch flag once we render this tab
    st.session_state["switch_to_chart"] = False

    st.header("Chart & Technical Signals")

    col_left, col_right = st.columns([2, 1])
    with col_left:
        current_ticker = st.session_state.get("chart_ticker", "NOKIA.HE")
        all_tickers = list(HELSINKI_STOCKS.keys())
        ticker_input = st.selectbox(
            "Stock",
            options=all_tickers,
            index=all_tickers.index(current_ticker) if current_ticker in all_tickers else 0,
            format_func=lambda t: f"{t}  —  {HELSINKI_STOCKS.get(t, t)}",
        )
        # Keep session state in sync if user manually changes the selectbox
        st.session_state["chart_ticker"] = ticker_input

    with col_right:
        timeframe = st.radio(
            "Timeframe",
            ["5m · 1d", "15m · 5d", "1h · 1mo", "1d · 6mo"],
            horizontal=True,
        )

    interval_map = {
        "5m · 1d":   ("5m",  "1d"),
        "15m · 5d":  ("15m", "5d"),
        "1h · 1mo":  ("1h",  "1mo"),
        "1d · 6mo":  ("1d",  "6mo"),
    }
    interval, period = interval_map[timeframe]

    # ── Overlays ──────────────────────────────────────────────────────────────
    ov1, ov2, ov3 = st.columns(3)
    show_ema  = ov1.checkbox("EMA 9 / 21 / 50", value=True)
    show_bb   = ov2.checkbox("Bollinger Bands", value=True)
    show_vwap = ov3.checkbox("VWAP", value=True)

    # ── Fetch & compute ───────────────────────────────────────────────────────
    with st.spinner(f"Loading {ticker_input} [{interval}]…"):
        if interval == "1d":
            df_chart = fetch_daily(ticker_input, period=period)
        else:
            df_chart = fetch_intraday(ticker_input, interval=interval, period=period)

    if df_chart.empty:
        st.error("No data returned for this ticker / timeframe combination.")
        st.stop()

    df_chart = add_indicators(df_chart)
    df_chart = generate_signals(df_chart)

    # ── KPI bar ───────────────────────────────────────────────────────────────
    last_price = df_chart["Close"].iloc[-1]
    prev_price = df_chart["Close"].iloc[-2] if len(df_chart) > 1 else last_price
    change_pct = (last_price - prev_price) / prev_price * 100
    last_rsi   = df_chart["RSI"].dropna().iloc[-1] if "RSI" in df_chart.columns else None
    last_sig   = last_signal(df_chart)
    atr        = df_chart["ATR"].dropna().iloc[-1] if "ATR" in df_chart.columns else None

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Last Price", f"€{last_price:.2f}", f"{change_pct:+.2f}%")
    k2.metric("RSI (14)", rsi_label(last_rsi))
    k3.metric("Last Signal", last_sig)
    k4.metric("ATR", f"{atr:.3f}" if atr else "—")

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = build_main_chart(df_chart, ticker_input, show_ema, show_bb, show_vwap)
    st.plotly_chart(fig, use_container_width=True)

    # ── Signal log ────────────────────────────────────────────────────────────
    if "Signal" in df_chart.columns:
        sig_log = df_chart.dropna(subset=["Signal"])[["Close", "Signal", "RSI", "MACD"]].copy()
        sig_log.index = (
            sig_log.index.strftime("%Y-%m-%d %H:%M")
            if hasattr(sig_log.index, "strftime") else sig_log.index
        )
        sig_log.columns = ["Price", "Signal", "RSI", "MACD"]
        if not sig_log.empty:
            st.subheader("Signal History")
            sig_style = sig_log.style
            style_fn2 = "map" if hasattr(sig_style, "map") else "applymap"
            sig_style = getattr(sig_style, style_fn2)(
                lambda v: "color: #26a69a" if v == "BUY" else "color: #ef5350",
                subset=["Signal"],
            ).format({"Price": "{:.2f}", "RSI": "{:.1f}", "MACD": "{:.4f}"})
            st.dataframe(sig_style, use_container_width=True, height=200)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        "⚠️ This tool is for informational purposes only. "
        "Signals are generated algorithmically and do not constitute financial advice. "
        "Past performance is not indicative of future results."
    )
