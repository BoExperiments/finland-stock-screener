"""Plotly chart builders for candlestick + indicators."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def build_main_chart(df: pd.DataFrame, ticker: str, show_ema: bool, show_bb: bool, show_vwap: bool) -> go.Figure:
    """Candlestick chart with optional overlays and RSI/MACD subplots."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.20, 0.25],
        subplot_titles=("", "RSI (14)", "MACD"),
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name=ticker,
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ), row=1, col=1)

    # Volume bars (secondary y — workaround: normalize to chart area)
    vol_norm = df["Volume"] / df["Volume"].max() * (df["Close"].max() - df["Close"].min()) * 0.2 + df["Close"].min()
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume",
        marker_color="rgba(100,149,237,0.3)",
        yaxis="y2",
        showlegend=False,
    ), row=1, col=1)

    if show_ema and "EMA9" in df.columns:
        for col, color, name in [("EMA9", "#ff9800", "EMA 9"), ("EMA21", "#2196f3", "EMA 21"), ("EMA50", "#9c27b0", "EMA 50")]:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=name,
                line=dict(color=color, width=1.2),
            ), row=1, col=1)

    if show_bb and "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="BB Upper",
            line=dict(color="rgba(173,216,230,0.6)", width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="BB Lower",
            line=dict(color="rgba(173,216,230,0.6)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(173,216,230,0.07)",
            showlegend=False,
        ), row=1, col=1)

    if show_vwap and "VWAP" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["VWAP"], name="VWAP",
            line=dict(color="#ffeb3b", width=1.5, dash="dash"),
        ), row=1, col=1)

    # Signal markers
    if "Signal" in df.columns:
        buys = df[df["Signal"] == "BUY"]
        sells = df[df["Signal"] == "SELL"]
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys.index, y=buys["Signal_Price"] * 0.998,
                mode="markers", name="BUY Signal",
                marker=dict(symbol="triangle-up", size=12, color="#00e676"),
            ), row=1, col=1)
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells.index, y=sells["Signal_Price"] * 1.002,
                mode="markers", name="SELL Signal",
                marker=dict(symbol="triangle-down", size=12, color="#ff1744"),
            ), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#e91e63", width=1.5),
        ), row=2, col=1)
        for level, color in [(70, "rgba(255,0,0,0.3)"), (30, "rgba(0,255,0,0.3)")]:
            fig.add_hline(y=level, line_dash="dot", line_color=color, row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"], name="MACD",
            line=dict(color="#00bcd4", width=1.5),
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"], name="Signal",
            line=dict(color="#ff9800", width=1.2),
        ), row=3, col=1)
        colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_hist"], name="Histogram",
            marker_color=colors, showlegend=False,
        ), row=3, col=1)

    fig.update_layout(
        title=dict(text=ticker, font=dict(size=16)),
        template="plotly_dark",
        height=750,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=0),
        margin=dict(l=40, r=40, t=60, b=20),
        yaxis2=dict(overlaying="y", side="right", showticklabels=False, showgrid=False),
    )
    fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="MACD", row=3, col=1)

    return fig
