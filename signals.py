"""Technical indicators and trade signal generation."""

import pandas as pd
import numpy as np
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add EMA, Bollinger Bands, VWAP, RSI, MACD to OHLCV dataframe."""
    if df.empty or len(df) < 20:
        return df

    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # EMAs
    df["EMA9"] = ta.trend.ema_indicator(close, window=9)
    df["EMA21"] = ta.trend.ema_indicator(close, window=21)
    df["EMA50"] = ta.trend.ema_indicator(close, window=50)

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_mid"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()

    # VWAP (resets daily — use cumulative for intraday)
    df["VWAP"] = (close * volume).cumsum() / volume.cumsum()

    # RSI
    df["RSI"] = ta.momentum.rsi(close, window=14)

    # MACD
    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()

    # ATR for volatility context
    df["ATR"] = ta.volatility.average_true_range(high, low, close, window=14)

    return df


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate BUY/SELL signal markers based on EMA crossover + RSI."""
    if df.empty or "EMA9" not in df.columns:
        return df

    df = df.copy()
    df["Signal"] = None
    df["Signal_Price"] = np.nan

    prev_ema9 = df["EMA9"].shift(1)
    prev_ema21 = df["EMA21"].shift(1)

    # BUY: EMA9 crosses above EMA21, RSI between 40-65 (not overbought)
    buy_mask = (
        (df["EMA9"] > df["EMA21"]) &
        (prev_ema9 <= prev_ema21) &
        (df["RSI"] > 40) &
        (df["RSI"] < 65)
    )

    # SELL: EMA9 crosses below EMA21, RSI between 35-60 (not oversold)
    sell_mask = (
        (df["EMA9"] < df["EMA21"]) &
        (prev_ema9 >= prev_ema21) &
        (df["RSI"] > 35) &
        (df["RSI"] < 60)
    )

    df.loc[buy_mask, "Signal"] = "BUY"
    df.loc[buy_mask, "Signal_Price"] = df.loc[buy_mask, "Close"]
    df.loc[sell_mask, "Signal"] = "SELL"
    df.loc[sell_mask, "Signal_Price"] = df.loc[sell_mask, "Close"]

    return df


def rsi_label(rsi: float) -> str:
    if rsi is None or pd.isna(rsi):
        return "N/A"
    if rsi >= 70:
        return f"🔴 {rsi:.1f} Overbought"
    if rsi <= 30:
        return f"🟢 {rsi:.1f} Oversold"
    return f"⚪ {rsi:.1f} Neutral"


def last_signal(df: pd.DataFrame) -> str:
    if "Signal" not in df.columns:
        return "—"
    sigs = df.dropna(subset=["Signal"])
    if sigs.empty:
        return "—"
    last = sigs.iloc[-1]
    ts = last.name.strftime("%H:%M") if hasattr(last.name, "strftime") else str(last.name)
    return f"{last['Signal']} @ {last['Signal_Price']:.2f} ({ts})"
