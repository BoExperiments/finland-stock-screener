"""Yahoo Finance data fetching with caching."""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


@st.cache_data(ttl=300)
def fetch_snapshot(tickers: list[str]) -> pd.DataFrame:
    """Fetch current-day snapshot for a list of tickers."""
    rows = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            hist = t.history(period="2d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue
            prev_close = hist["Close"].iloc[-2]
            last_close = hist["Close"].iloc[-1]
            vol_today = hist["Volume"].iloc[-1]

            hist20 = t.history(period="1mo", interval="1d")
            avg_vol = hist20["Volume"].mean() if not hist20.empty else 0

            change_pct = ((last_close - prev_close) / prev_close) * 100
            vol_ratio = vol_today / avg_vol if avg_vol > 0 else 0

            rows.append({
                "Ticker": ticker,
                "Name": ticker.replace(".HE", ""),
                "Price": round(last_close, 2),
                "Change %": round(change_pct, 2),
                "Volume": int(vol_today),
                "Vol/Avg": round(vol_ratio, 2),
                "Avg Vol (20d)": int(avg_vol),
                "Market Cap": getattr(info, "market_cap", None),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def fetch_intraday(ticker: str, interval: str = "5m", period: str = "1d") -> pd.DataFrame:
    """Fetch intraday OHLCV data."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    df.index = pd.to_datetime(df.index)
    return df


@st.cache_data(ttl=300)
def fetch_daily(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch daily OHLCV data."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval="1d")
    df.index = pd.to_datetime(df.index)
    return df
