"""
dashboard.py – Real-time Streamlit trading dashboard.

Run with:
    streamlit run dashboard/dashboard.py

Features:
  • Live account equity & P&L card
  • Portfolio value chart (line)
  • Executed trades table
  • REFUSED trades table (prominently displayed)
  • Sentiment log
  • Auto-refresh every 60 s
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.logger import (
    read_trades,
    read_refused_trades,
    read_sentiment_log,
    read_portfolio_history,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="News-Sentiment Options Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Dark gradient background */
    .stApp { background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%); }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(145deg, #1c2333, #21262d);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e6edf3 !important; font-weight: 700; }

    /* Section headers */
    .section-header {
        color: #58a6ff;
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        padding: 8px 0 4px;
        border-bottom: 1px solid #21262d;
        margin-bottom: 12px;
    }

    /* REFUSED badge */
    .refused-badge {
        background: linear-gradient(135deg, #da3633 0%, #b91c1c 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 1px;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* APPROVED badge */
    .approved-badge {
        background: linear-gradient(135deg, #238636 0%, #16a34a 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 1px;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* Dataframe styling */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background: #21262d !important; color: #58a6ff !important; }

    /* Top banner */
    .top-banner {
        background: linear-gradient(90deg, #0d419d 0%, #1f6feb 50%, #388bfd 100%);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .top-banner h1 { color: white; margin: 0; font-size: 1.6rem; font-weight: 700; }
    .top-banner p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem; }

    /* Status pill */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(35,134,54,0.2);
        border: 1px solid #238636;
        border-radius: 20px;
        padding: 4px 14px;
        color: #3fb950;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .status-dot { width: 8px; height: 8px; background: #3fb950; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="top-banner">
      <div>
        <h1>📈 News-Sentiment Options Agent</h1>
        <p>Autonomous • Claude AI • Alpaca Paper Trading • Real-time Risk Gate</p>
      </div>
      <div style="margin-left:auto">
        <span class="status-pill"><span class="status-dot"></span> LIVE</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
refresh_interval = st.sidebar.slider("Auto-refresh (seconds)", 10, 300, 60)
st.sidebar.markdown("---")
st.sidebar.markdown("**Hackathon**: Alpaca × lablab.ai 2026")
st.sidebar.markdown("**Strategy**: News-Sentiment → Options")

# ── Load data ─────────────────────────────────────────────────────────────────
trades         = read_trades()
refused_trades = read_refused_trades()
sentiment_log  = read_sentiment_log()
portfolio_hist = read_portfolio_history()

df_trades   = pd.DataFrame(trades)         if trades         else pd.DataFrame()
df_refused  = pd.DataFrame(refused_trades) if refused_trades else pd.DataFrame()
df_sent     = pd.DataFrame(sentiment_log)  if sentiment_log  else pd.DataFrame()
df_port     = pd.DataFrame(portfolio_hist) if portfolio_hist  else pd.DataFrame()

# ── Metrics row ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

current_equity = df_port["equity"].iloc[-1]         if not df_port.empty and "equity" in df_port else 100_000
initial_equity = df_port["equity"].iloc[0]          if not df_port.empty and "equity" in df_port else 100_000
total_pnl      = current_equity - initial_equity
open_positions = int(df_port["open_positions"].iloc[-1]) if not df_port.empty and "open_positions" in df_port else 0

col1.metric("💰 Portfolio Value",   f"${current_equity:,.2f}")
col2.metric("📊 Total P&L",         f"${total_pnl:+,.2f}",  f"{(total_pnl/initial_equity*100):+.2f}%")
col3.metric("✅ Executed Trades",   len(trades))
col4.metric("❌ Refused Trades",    len(refused_trades), help="Risk-gate rejections")
col5.metric("📋 Open Positions",    open_positions)

st.markdown("---")

# ── Portfolio Chart ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 Portfolio Equity Over Time</div>', unsafe_allow_html=True)

if not df_port.empty and "equity" in df_port and "timestamp" in df_port:
    df_port["timestamp"] = pd.to_datetime(df_port["timestamp"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_port["timestamp"],
        y=df_port["equity"],
        mode="lines+markers",
        name="Equity",
        line=dict(color="#58a6ff", width=2.5),
        marker=dict(size=4),
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.07)",
    ))
    fig.add_hline(y=100_000, line_dash="dot", line_color="#3fb950", annotation_text="Start $100K")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(22,27,34,0.7)",
        font=dict(color="#8b949e", family="Inter"),
        xaxis=dict(gridcolor="#21262d", showgrid=True),
        yaxis=dict(gridcolor="#21262d", showgrid=True, tickprefix="$"),
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No portfolio history yet – run the agent to populate data.")

# ── Tabs for tables ───────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["✅ Executed Trades", "❌ Refused Trades", "🧠 Sentiment Log"])

# ── Executed Trades ───────────────────────────────────────────────────────────
with tab1:
    st.markdown('<span class="approved-badge">EXECUTED</span>', unsafe_allow_html=True)
    if df_trades.empty:
        st.info("No trades executed yet.")
    else:
        cols_to_show = [c for c in ["timestamp","ticker","option_type","symbol","strike","contracts","mid_price","estimated_cost","status"] if c in df_trades.columns]
        display = df_trades[cols_to_show].sort_values("timestamp", ascending=False) if "timestamp" in df_trades.columns else df_trades[cols_to_show]
        st.dataframe(
            display.rename(columns={
                "timestamp": "Time (UTC)", "option_type": "Type",
                "mid_price": "Fill Price", "estimated_cost": "Cost ($)",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ── Refused Trades ────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<span class="refused-badge">🚫 REFUSED BY RISK GATE</span>', unsafe_allow_html=True)
    st.caption("These are proposals that Claude generated but our deterministic risk gate blocked.")
    if df_refused.empty:
        st.success("No trades refused yet – all proposals passed the risk gate.")
    else:
        cols_to_show = [c for c in ["timestamp","ticker","option_type","symbol","cost","reason"] if c in df_refused.columns]
        display = df_refused[cols_to_show].sort_values("timestamp", ascending=False) if "timestamp" in df_refused.columns else df_refused[cols_to_show]

        # Colour-code refusal reasons
        def highlight_reason(val):
            colours = {
                "Outside market hours":     "#1c1010",
                "Max positions":            "#1c1010",
                "Daily loss limit":         "#200a0a",
                "Trade cost":               "#1a1010",
                "Concentration":            "#18100a",
                "Confidence":               "#101820",
            }
            for k, bg in colours.items():
                if k in str(val):
                    return f"background-color: {bg}; color: #f97583"
            return "color: #f97583"

        styled = display.style.map(highlight_reason, subset=["reason"] if "reason" in display.columns else [])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Pie chart of refusal reasons
        if "reason" in df_refused.columns:
            reason_counts = df_refused["reason"].str.split("(").str[0].str.strip().value_counts().reset_index()
            reason_counts.columns = ["Reason", "Count"]
            fig2 = px.pie(
                reason_counts, values="Count", names="Reason",
                title="Refusal Reason Breakdown",
                color_discrete_sequence=px.colors.sequential.Reds_r,
                hole=0.4,
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b949e", family="Inter"),
                height=300,
                margin=dict(l=0, r=0, t=30, b=0),
            )
            st.plotly_chart(fig2, use_container_width=True)

# ── Sentiment Log ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🧠 Claude Sentiment Analysis Log</div>', unsafe_allow_html=True)
    if df_sent.empty:
        st.info("No sentiment data yet.")
    else:
        cols_to_show = [c for c in ["timestamp","ticker","sentiment","confidence","suggested_trade","reasoning"] if c in df_sent.columns]
        display = df_sent[cols_to_show].sort_values("timestamp", ascending=False) if "timestamp" in df_sent.columns else df_sent[cols_to_show]

        def colour_sentiment(val):
            if val == "BULLISH":  return "color: #3fb950; font-weight:600"
            if val == "BEARISH":  return "color: #f97583; font-weight:600"
            return "color: #e3b341; font-weight:600"

        if "sentiment" in display.columns:
            styled2 = display.style.map(colour_sentiment, subset=["sentiment"])
            st.dataframe(styled2, use_container_width=True, hide_index=True)
        else:
            st.dataframe(display, use_container_width=True, hide_index=True)

        # Sentiment distribution bar chart
        if "sentiment" in df_sent.columns and "ticker" in df_sent.columns:
            pivot = df_sent.groupby(["ticker","sentiment"]).size().reset_index(name="count")
            color_map = {"BULLISH": "#3fb950", "BEARISH": "#f97583", "NEUTRAL": "#e3b341"}
            fig3 = px.bar(
                pivot, x="ticker", y="count", color="sentiment",
                color_discrete_map=color_map,
                barmode="group",
                title="Sentiment Breakdown by Ticker",
            )
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(22,27,34,0.7)",
                font=dict(color="#8b949e", family="Inter"),
                xaxis=dict(gridcolor="#21262d"),
                yaxis=dict(gridcolor="#21262d"),
                height=280,
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig3, use_container_width=True)

# ── Footer + auto-refresh ─────────────────────────────────────────────────────
st.markdown("---")
st.caption("🤖 Autonomous agent running every 30 min • AI suggests • Code decides • Full audit trail")

# Streamlit auto-rerun
import time as _time
_time.sleep(refresh_interval)
st.rerun()
