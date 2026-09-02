"""
dashboard.py – Sentinel Options • Interactive Mission Control & Trading Dashboard (Modern Light Theme)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.config import Config
from src.logger import (
    read_trades, read_refused_trades,
    read_sentiment_log, read_portfolio_history,
)
from src.news_fetcher import NewsFetcher
from src.sentiment_analyzer import SentimentAnalyzer
from src.trade_proposer import TradeProposer
from src.risk_gate import RiskGate
from src.position_monitor import PositionMonitor
from src.agent_controller import AgentController

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinel Options • Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Light Theme CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ── Base Theme: Crisp Soft Light ── */
.stApp {
    background: radial-gradient(ellipse at top left, #f8fafc 0%, #f1f5f9 40%, #ffffff 100%);
    color: #0f172a;
    min-height: 100vh;
}

/* ── Hide default chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 2.5rem; max-width: 100%; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 18px 22px;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px -4px rgba(99, 102, 241, 0.12);
    border-color: #cbd5e1;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #6366f1, #06b6d4, #10b981);
}
[data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.74rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1.2px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-size: 1.9rem !important;
    font-weight: 800 !important;
    line-height: 1.1 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; font-weight: 700 !important; }

/* ── Interactive Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 0.6rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.55) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 5px;
    gap: 6px;
}
.stTabs [data-baseweb="tab"] {
    color: #64748b;
    border-radius: 8px;
    font-size: 0.86rem;
    font-weight: 600;
    padding: 8px 20px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #4338ca !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── DataFrames ── */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0;
}

/* ── Inputs ── */
.stTextInput > div > div > input, .stSlider {
    color: #0f172a !important;
}

/* ── Animations ── */
@keyframes pulse-ring {
    0%   { transform: scale(1);   opacity: 1; }
    70%  { transform: scale(1.6); opacity: 0; }
    100% { transform: scale(1);   opacity: 0; }
}
@keyframes ticker-scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px; padding-bottom:12px; border-bottom:1px solid #e2e8f0;">
        <div style="font-size:1.6rem;">⚡</div>
        <div>
            <div style="font-size:1.05rem; font-weight:800; color:#0f172a; letter-spacing:0.3px;">MISSION CONTROL</div>
            <div style="font-size:0.7rem; color:#64748b; font-weight:600;">Autonomous Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### 🎮 Live Execution")
    trigger_cycle = st.button("🚀 Trigger Full Cycle Now", use_container_width=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("##### 📡 UI Controls")
    auto_refresh = st.checkbox("Auto-refresh UI (60s)", value=True)
    if st.button("🔄 Refresh Telemetry", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#64748b; line-height:1.5;">
        <b style="color:#0f172a;">Sentinel Architecture:</b><br>
        1. Live News Scraping<br>
        2. Multi-Head Sentiment Signal<br>
        3. Dynamic ATM Option Selection<br>
        4. Deterministic Risk Gate<br>
        5. Position Lifecycle Exits
    </div>
    """, unsafe_allow_html=True)

# ── Header Banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    margin-bottom: 16px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.04);
    position: relative;
    overflow: hidden;
">
    <div style="position:absolute; top:0; left:0; right:0; height:3px;
                background: linear-gradient(90deg, #6366f1, #06b6d4, #10b981);"></div>
    <div style="display:flex; align-items:center; gap:16px;">
        <div style="
            width: 48px; height: 48px;
            background: linear-gradient(135deg, #6366f1, #06b6d4);
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem;
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
        ">⚡</div>
        <div>
            <div style="
                font-size: 1.65rem;
                font-weight: 900;
                color: #0f172a;
                letter-spacing: -0.5px;
                line-height: 1.1;
            ">SENTINEL OPTIONS</div>
            <div style="color: #64748b; font-size: 0.78rem; font-weight: 600;
                        letter-spacing: 1.2px; text-transform: uppercase; margin-top: 2px;">
                Autonomous Options Engine · Multi-Head Sentiment Signal · Deterministic Risk Gate
            </div>
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <div style="
            display: flex; align-items: center; gap: 8px;
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            border-radius: 30px;
            padding: 6px 16px;
        ">
            <div style="position:relative; width:9px; height:9px;">
                <div style="position:absolute; inset:0; background:#10b981; border-radius:50%;
                            animation: pulse-ring 2s ease-out infinite;"></div>
                <div style="width:9px; height:9px; background:#10b981; border-radius:50%;"></div>
            </div>
            <span style="color:#059669; font-size:0.8rem; font-weight:800; letter-spacing:0.8px;">SYSTEM ACTIVE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Polished Engine Parameters Bar (Replacing weird text with modern cards) ────
st.markdown(f"""
<div style="
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
">
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px 16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-size:0.68rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.8px;">Trading Mode</div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">{'Paper Trading' if 'paper' in Config.ALPACA_BASE_URL else 'Live Trading'}</div>
        <div style="font-size:0.7rem; color:#10b981; font-weight:600; margin-top:2px;">● Connected to Alpaca</div>
    </div>
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px 16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-size:0.68rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.8px;">Active Watchlist</div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">{', '.join(Config.WATCHLIST)}</div>
        <div style="font-size:0.7rem; color:#6366f1; font-weight:600; margin-top:2px;">● {len(Config.WATCHLIST)} Target Equities</div>
    </div>
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px 16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-size:0.68rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.8px;">Max Allocation / Trade</div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">${Config.MAX_LOSS_PER_TRADE:,.0f}</div>
        <div style="font-size:0.7rem; color:#0ea5e9; font-weight:600; margin-top:2px;">● Risk Gate Hard Ceiling</div>
    </div>
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:12px 16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
        <div style="font-size:0.68rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.8px;">Exit Rules</div>
        <div style="font-size:0.95rem; font-weight:800; color:#0f172a; margin-top:2px;">+{int(Config.TAKE_PROFIT_PCT*100)}% / -{int(Config.STOP_LOSS_PCT*100)}%</div>
        <div style="font-size:0.7rem; color:#f59e0b; font-weight:600; margin-top:2px;">● Auto Take-Profit & Stop-Loss</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Live Cycle Execution Stepper ──────────────────────────────────────────────
if trigger_cycle:
    st.markdown("#### ⚡ Live Pipeline Telemetry")
    progress_bar = st.progress(0)
    status_box = st.empty()
    live_log = st.empty()

    try:
        controller = AgentController()
        
        # Step 0
        status_box.markdown("**[Step 0/5]** 🔍 Monitoring existing portfolio positions for exit triggers...")
        progress_bar.progress(15)
        closed = controller.monitor.check_exits()
        time.sleep(0.4)

        # Step 1
        status_box.markdown("**[Step 1/5]** 📰 Scraping live financial news feeds across universe...")
        progress_bar.progress(35)
        news = controller.fetcher.fetch_all(controller.watchlist)
        total_arts = sum(len(v) for v in news.values())
        live_log.info(f"Scraped {total_arts} recent articles across {len(news)} tickers.")
        time.sleep(0.4)

        # Step 2
        status_box.markdown("**[Step 2/5]** 🧠 Running multi-head sentiment inference & signal extraction...")
        progress_bar.progress(60)
        sentiments = controller.analyzer.analyze_all(news)
        live_log.write(f"Generated {len(sentiments)} actionable market assessments.")
        time.sleep(0.4)

        # Step 3
        status_box.markdown("**[Step 3/5]** 🎯 Resolving option chains & selecting optimal ATM contracts...")
        progress_bar.progress(75)
        proposals = controller.proposer.propose_all(sentiments)
        live_log.write(f"Drafted {len(proposals)} option contract proposals.")
        time.sleep(0.4)

        # Step 4
        status_box.markdown("**[Step 4/5]** 🛡️ Enforcing deterministic mathematical risk gate...")
        progress_bar.progress(90)
        approved = []
        for prop in proposals:
            ok, reason = controller.risk_gate.check(prop)
            if ok:
                approved.append(prop)
        live_log.write(f"Risk gate verdict: {len(approved)} approved, {len(proposals)-len(approved)} refused.")
        time.sleep(0.4)

        # Step 5
        status_box.markdown("**[Step 5/5]** 🚀 Submitting approved orders & updating audit ledger...")
        progress_bar.progress(100)
        if approved:
            results = controller.executor.execute_all(approved)
            live_log.success(f"Executed {len(results)} orders!")
        else:
            live_log.info("No approved trades to execute in this cycle.")

        controller.portfolio.snapshot()
        st.success("✅ Full Sentinel trading cycle executed successfully!")
        time.sleep(1.2)
        st.rerun()

    except Exception as exc:
        st.error(f"Execution encountered an exception: {exc}")

# ── Load Data ─────────────────────────────────────────────────────────────────
trades         = read_trades()         or []
refused_trades = read_refused_trades() or []
sentiment_log  = read_sentiment_log()  or []
portfolio_hist = read_portfolio_history() or []

df_trades  = pd.DataFrame(trades)
df_refused = pd.DataFrame(refused_trades)
df_sent    = pd.DataFrame(sentiment_log)
df_port    = pd.DataFrame(portfolio_hist)

# ── Compute Key Metrics ───────────────────────────────────────────────────────
START_EQUITY   = 100_000
cur_equity     = float(df_port["equity"].iloc[-1])        if not df_port.empty and "equity"         in df_port else START_EQUITY
open_positions = int(df_port["open_positions"].iloc[-1])  if not df_port.empty and "open_positions" in df_port else 0
total_pnl      = cur_equity - START_EQUITY
pnl_pct        = (total_pnl / START_EQUITY) * 100

# ── Top Metric Cards ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💼 Account Equity", f"${cur_equity:,.0f}")
c2.metric("📈 Net P&L",        f"${total_pnl:+,.0f}",   f"{pnl_pct:+.2f}%")
c3.metric("✅ Executed Orders", len(trades))
c4.metric("🚫 Gate Refusals",   len(refused_trades), help="Proposals blocked by deterministic rules")
c5.metric("📋 Open Positions",  open_positions)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ── Live Sentiment Ticker Bar ─────────────────────────────────────────────────
if not df_sent.empty and "ticker" in df_sent and "sentiment" in df_sent:
    latest = df_sent.drop_duplicates("ticker", keep="last").to_dict("records")
    def sent_color(s):
        return {"BULLISH":"#059669","BEARISH":"#e11d48","NEUTRAL":"#d97706"}.get(s,"#475569")
    def sent_icon(s):
        return {"BULLISH":"▲","BEARISH":"▼","NEUTRAL":"◆"}.get(s,"·")

    items = "".join([
        f'<span style="margin:0 24px; color:#cbd5e1">|</span>'
        f'<span style="color:#0f172a; font-weight:800; font-size:0.88rem;">{r["ticker"]}</span>'
        f'<span style="color:{sent_color(r["sentiment"])}; margin-left:6px; font-weight:800; font-size:0.88rem;">'
        f'{sent_icon(r["sentiment"])} {r["sentiment"]}</span>'
        f'<span style="color:{sent_color(r["sentiment"])}; margin-left:5px; font-size:0.78rem; font-weight:700;">'
        f'{float(r.get("confidence",0))*100:.0f}%</span>'
        for r in latest
    ] * 3)

    st.markdown(f"""
    <div style="
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 9px 0;
        overflow: hidden;
        margin-bottom: 20px;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    ">
        <div style="
            display: inline-block;
            animation: ticker-scroll 24s linear infinite;
            padding: 0 20px;
            font-family: 'JetBrains Mono', monospace;
        ">{items}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Primary Visualizations Row ────────────────────────────────────────────────
col_chart, col_donut = st.columns([3, 1])

with col_chart:
    st.markdown("""
    <div style="color:#475569; font-size:0.75rem; text-transform:uppercase;
                letter-spacing:1.5px; font-weight:700; margin-bottom:8px;">
        ◈ Portfolio Equity Curve
    </div>""", unsafe_allow_html=True)

    if not df_port.empty and "equity" in df_port and "timestamp" in df_port:
        df_port["timestamp"] = pd.to_datetime(df_port["timestamp"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_port["timestamp"], y=df_port["equity"],
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.06)",
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df_port["timestamp"], y=df_port["equity"],
            mode="lines+markers",
            line=dict(color="#6366f1", width=2.5, shape="spline"),
            marker=dict(size=5, color="#06b6d4", line=dict(color="#ffffff", width=2)),
            name="Equity",
            hovertemplate="<b>$%{y:,.2f}</b><br>%{x}<extra></extra>",
        ))
        fig.add_hline(
            y=START_EQUITY,
            line=dict(color="#cbd5e1", dash="dot", width=1.5),
            annotation_text="Base $100K",
            annotation_font=dict(color="#64748b", size=10),
        )
        fig.update_layout(
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#475569", family="Inter"),
            xaxis=dict(gridcolor="#f1f5f9", showgrid=True, zeroline=False),
            yaxis=dict(gridcolor="#f1f5f9", showgrid=True, zeroline=False, tickprefix="$"),
            height=260, margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity curve yet — click 'Trigger Full Cycle Now' in the sidebar to populate.")

with col_donut:
    st.markdown("""
    <div style="color:#475569; font-size:0.75rem; text-transform:uppercase;
                letter-spacing:1.5px; font-weight:700; margin-bottom:8px;">
        ◈ Signal Distribution
    </div>""", unsafe_allow_html=True)

    if not df_sent.empty and "sentiment" in df_sent:
        counts = df_sent["sentiment"].value_counts()
        colors = {"BULLISH":"#10b981","BEARISH":"#f43f5e","NEUTRAL":"#f59e0b"}
        fig2 = go.Figure(go.Pie(
            labels=counts.index,
            values=counts.values,
            hole=0.66,
            marker_colors=[colors.get(l,"#94a3b8") for l in counts.index],
            textfont=dict(size=11, color="white"),
            hovertemplate="<b>%{label}</b>: %{value} signals<extra></extra>",
        ))
        fig2.add_annotation(
            text=f"<b>{len(df_sent)}</b><br><span style='font-size:10px; color:#64748b'>TOTAL</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=15, color="#0f172a"),
        )
        fig2.update_layout(
            paper_bgcolor="#ffffff",
            font=dict(color="#475569", family="Inter"),
            height=260, margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(
                font=dict(size=10, color="#475569"),
                orientation="h", x=0.5, xanchor="center", y=-0.15,
            ),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown("<div style='color:#94a3b8; font-size:0.85rem; padding:40px 0;'>No sentiment records yet.</div>", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Main Tabs: Data & Interactive Tools ───────────────────────────────────────
tab_exec, tab_refused, tab_sentiment, tab_sandbox = st.tabs([
    "⚡ Executed Trades",
    "🚫 Risk Gate Audit",
    "🧠 Sentiment Intelligence",
    "🧪 Interactive AI Sandbox & Simulator",
])

CHART_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(color="#475569", family="Inter"),
    height=250,
    margin=dict(l=10, r=10, t=24, b=10),
    legend=dict(bgcolor="rgba(255,255,255,0.9)"),
    xaxis=dict(gridcolor="#f1f5f9"),
    yaxis=dict(gridcolor="#f1f5f9"),
)

# ── Tab 1: Executed Trades ────────────────────────────────────────────────────
with tab_exec:
    if df_trades.empty:
        st.markdown("""
        <div style="padding:40px; text-align:center; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;">
            <div style="font-size:2.2rem; margin-bottom:10px;">📭</div>
            <div style="font-weight:700; font-size:1rem; color:#0f172a;">No orders placed yet</div>
            <div style="font-size:0.82rem; color:#64748b; margin-top:4px;">Orders execute during live market hours when high-confidence signals pass the risk gate.</div>
        </div>""", unsafe_allow_html=True)
    else:
        cols = [c for c in ["timestamp","ticker","option_type","symbol","strike",
                             "contracts","mid_price","estimated_cost","status"] if c in df_trades]
        disp = df_trades[cols].sort_values("timestamp", ascending=False) if "timestamp" in df_trades else df_trades[cols]
        disp = disp.rename(columns={
            "timestamp":"Time","option_type":"Type",
            "mid_price":"Fill $","estimated_cost":"Cost $",
        })

        def color_type(v):
            if str(v).lower() == "call": return "color:#059669; font-weight:800"
            if str(v).lower() == "put":  return "color:#e11d48; font-weight:800"
            return ""

        st.dataframe(disp.style.map(color_type, subset=["Type"] if "Type" in disp else []),
                     use_container_width=True, hide_index=True)

# ── Tab 2: Refused Trades ─────────────────────────────────────────────────────
with tab_refused:
    if df_refused.empty:
        st.markdown("""
        <div style="padding:40px; text-align:center; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;">
            <div style="font-size:2.2rem; margin-bottom:10px;">🛡️</div>
            <div style="font-weight:700; font-size:1rem; color:#0f172a;">No gate refusals recorded</div>
        </div>""", unsafe_allow_html=True)
    else:
        c_left, c_right = st.columns([3, 2])
        with c_left:
            cols = [c for c in ["timestamp","ticker","option_type","reason"] if c in df_refused]
            disp = df_refused[cols].sort_values("timestamp", ascending=False) if "timestamp" in df_refused else df_refused[cols]
            styled = disp.style.map(lambda v: "color:#e11d48; font-size:0.82rem; font-weight:600;", subset=["reason"] if "reason" in disp else [])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        with c_right:
            if "reason" in df_refused.columns:
                reason_counts = (df_refused["reason"]
                                 .str.split("(").str[0].str.strip()
                                 .value_counts().reset_index())
                reason_counts.columns = ["Reason","Count"]
                fig4 = go.Figure(go.Bar(
                    x=reason_counts["Count"],
                    y=reason_counts["Reason"],
                    orientation="h",
                    marker=dict(
                        color=reason_counts["Count"],
                        colorscale=[[0,"#6366f1"],[1,"#f43f5e"]],
                    ),
                    hovertemplate="<b>%{y}</b>: %{x}<extra></extra>",
                ))
                fig4.update_layout(**CHART_LAYOUT, title="Refusal Reasons Breakdown")
                st.plotly_chart(fig4, use_container_width=True)

# ── Tab 3: Sentiment Intelligence ─────────────────────────────────────────────
with tab_sentiment:
    if df_sent.empty:
        st.markdown("""
        <div style="padding:40px; text-align:center; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px;">
            <div style="font-size:2.2rem; margin-bottom:10px;">🧠</div>
            <div style="font-weight:700; font-size:1rem; color:#0f172a;">No sentiment history found</div>
        </div>""", unsafe_allow_html=True)
    else:
        c_sent, c_bar = st.columns([3, 2])
        with c_sent:
            cols = [c for c in ["timestamp","ticker","sentiment","confidence",
                                 "suggested_trade","reasoning"] if c in df_sent]
            disp = df_sent[cols].sort_values("timestamp", ascending=False) if "timestamp" in df_sent else df_sent[cols]

            def color_sent(v):
                return {
                    "BULLISH": "color:#059669; font-weight:800",
                    "BEARISH": "color:#e11d48; font-weight:800",
                    "NEUTRAL": "color:#d97706; font-weight:800",
                }.get(v, "")

            styled3 = disp.style.map(color_sent, subset=["sentiment"] if "sentiment" in disp else [])
            st.dataframe(styled3, use_container_width=True, hide_index=True)

        with c_bar:
            if "sentiment" in df_sent and "ticker" in df_sent:
                pivot = (df_sent.groupby(["ticker","sentiment"]).size().reset_index(name="n"))
                fig5 = px.bar(
                    pivot, x="ticker", y="n", color="sentiment",
                    color_discrete_map={"BULLISH":"#10b981","BEARISH":"#f43f5e","NEUTRAL":"#f59e0b"},
                    barmode="group",
                )
                fig5.update_layout(**CHART_LAYOUT, title="Sentiment Signal Breakdown")
                st.plotly_chart(fig5, use_container_width=True)

# ── Tab 4: Interactive AI Sandbox & Simulator ─────────────────────────────────
with tab_sandbox:
    st.markdown("##### 🧪 On-Demand Market Intelligence & Option Proposer")
    st.caption("Test how the autonomous pipeline evaluates any ticker, reads live news, and checks option pricing in real-time.")

    sb_col1, sb_col2 = st.columns([1, 2])
    with sb_col1:
        test_ticker = st.text_input("Enter Ticker Symbol", value="NVDA").upper().strip()
        num_news = st.slider("News Headlines to Fetch", min_value=3, max_value=15, value=7)
        run_test_btn = st.button("🔍 Analyze & Propose Option", use_container_width=True)

    with sb_col2:
        if run_test_btn and test_ticker:
            sandbox_status = st.empty()
            sandbox_prog = st.progress(10)
            
            sandbox_status.markdown(f"**Step 1/3**: Scraping Google News for `{test_ticker}`...")
            fetcher = NewsFetcher()
            articles = fetcher.fetch(test_ticker, max_results=num_news)
            sandbox_prog.progress(40)
            
            sandbox_status.markdown(f"**Step 2/3**: Running neural sentiment inference for `{test_ticker}`...")
            analyzer = SentimentAnalyzer()
            signal = analyzer.analyze(test_ticker, articles)
            sandbox_prog.progress(75)
            
            sandbox_status.markdown(f"**Step 3/3**: Resolving option chain & checking risk constraints...")
            proposer = TradeProposer()
            gate = RiskGate()
            sandbox_prog.progress(100)
            sandbox_status.empty()

            st.write(f"📰 **Analyzed {len(articles)} recent articles for {test_ticker}**")

            if signal:
                sentiment = signal.get("sentiment", "NEUTRAL")
                conf = float(signal.get("confidence", 0))
                trade = signal.get("suggested_trade")
                reasoning = signal.get("reasoning", "")

                color = "#059669" if sentiment == "BULLISH" else ("#e11d48" if sentiment == "BEARISH" else "#d97706")
                st.markdown(f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:18px; margin:10px 0; box-shadow:0 4px 12px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.25rem; font-weight:800; color:#0f172a;">{test_ticker}</span>
                        <span style="font-size:1rem; font-weight:800; color:{color};">{sentiment} ({conf*100:.0f}%)</span>
                    </div>
                    <div style="font-size:0.88rem; color:#334155; margin-top:8px; line-height:1.5;"><b>Reasoning:</b> {reasoning}</div>
                    <div style="font-size:0.88rem; color:#4f46e5; font-weight:700; margin-top:8px;"><b>Suggested Trade:</b> {trade or 'None'}</div>
                </div>
                """, unsafe_allow_html=True)

                if trade:
                    st.markdown("##### 🎯 Selected Option Contract")
                    prop = proposer.propose(signal)
                    if prop:
                        st.json(prop)
                        approved, reason = gate.check(prop)
                        if approved:
                            st.success("✅ **Risk Gate PASSED** – Contract would be submitted live!")
                        else:
                            st.warning(f"❌ **Risk Gate REFUSED**: {reason}")
                    else:
                        st.info("No matching ATM contract found within 7–45 DTE range.")
            else:
                st.error("Failed to generate sentiment analysis.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid #e2e8f0;
    padding-top: 16px;
    color: #64748b;
    font-size: 0.76rem;
">
    <div>⚡ Sentinel Options • Autonomous Trading Engine</div>
    <div style="font-family:'JetBrains Mono',monospace;">NLP Pipeline → Contract Engine → Deterministic Risk Gate</div>
    <div>Auto-refreshes every 60s</div>
</div>
""", unsafe_allow_html=True)

# ── Auto-Refresh Handling ─────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()
