"""
dashboard.py – Sentinel Options • Hackathon Submission Dashboard
Alpaca AI Trading Agents Hackathon | lablab.ai × Alpaca | Aug 28 – Sep 4, 2026
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
from src.news_fetcher import NewsFetcher, fetch_news_for_watchlist
from src.sentiment_analyzer import SentimentAnalyzer
from src.trade_proposer import TradeProposer
from src.risk_gate import RiskGate
from src.position_monitor import PositionMonitor
from src.portfolio_tracker import PortfolioTracker
from src.trade_executor import TradeExecutor

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinel Options – Alpaca AI Hackathon",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

.stApp {
    background: linear-gradient(160deg, #f0f4ff 0%, #f8fafc 40%, #ffffff 100%);
    color: #0f172a;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.2rem 2rem 2rem; max-width: 100%; }

/* ── Cards ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 2px 12px rgba(15,23,42,0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99,102,241,0.1);
}
[data-testid="metric-container"]::before {
    content: ''; position: absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, #6366f1, #06b6d4, #10b981);
}
[data-testid="metric-container"] label {
    color: #64748b !important; font-size:0.7rem !important;
    text-transform: uppercase !important; letter-spacing:1.2px !important; font-weight:700 !important;
}
[data-testid="stMetricValue"] {
    color: #0f172a !important; font-size:1.75rem !important; font-weight:800 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
    padding: 0.6rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.3) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #f1f5f9; border:1px solid #e2e8f0; border-radius:12px; padding:4px; gap:4px;
}
.stTabs [data-baseweb="tab"] {
    color:#64748b; border-radius:8px; font-size:0.84rem; font-weight:600; padding:8px 18px; border:none;
}
.stTabs [aria-selected="true"] {
    background:#fff !important; color:#4338ca !important;
    box-shadow:0 2px 8px rgba(15,23,42,0.06) !important;
    border:1px solid #e2e8f0 !important;
}

.stDataFrame { border-radius:12px; overflow:hidden; border:1px solid #e2e8f0 !important; }
[data-testid="stSidebar"] { background:#fff !important; border-right:1px solid #e2e8f0; }

@keyframes pulse-ring {
    0%{ transform:scale(1); opacity:1; }
    70%{ transform:scale(1.6); opacity:0; }
    100%{ transform:scale(1); opacity:0; }
}
@keyframes ticker-scroll {
    0%{ transform:translateX(0); } 100%{ transform:translateX(-50%); }
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="
    display:flex; align-items:center; justify-content:space-between;
    padding:16px 22px; margin-bottom:14px;
    background:#ffffff; border:1px solid #e2e8f0; border-radius:16px;
    box-shadow:0 2px 12px rgba(15,23,42,0.04); position:relative; overflow:hidden;
">
    <div style="position:absolute;top:0;left:0;right:0;height:3px;
                background:linear-gradient(90deg,#6366f1,#06b6d4,#10b981);"></div>
    <div style="display:flex;align-items:center;gap:14px;">
        <div style="width:44px;height:44px;background:linear-gradient(135deg,#6366f1,#06b6d4);
                    border-radius:12px;display:flex;align-items:center;justify-content:center;
                    font-size:1.4rem;color:#fff;box-shadow:0 4px 14px rgba(99,102,241,0.3);">⚡</div>
        <div>
            <div style="font-size:1.5rem;font-weight:900;color:#0f172a;letter-spacing:-0.5px;">SENTINEL OPTIONS</div>
            <div style="color:#64748b;font-size:0.72rem;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;">
                Autonomous Options Trading Agent · Alpaca Paper · AI-Driven Sentiment
            </div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <div style="background:#f0fdf4;border:1px solid #a7f3d0;border-radius:30px;padding:5px 14px;
                    display:flex;align-items:center;gap:7px;">
            <div style="position:relative;width:8px;height:8px;">
                <div style="position:absolute;inset:0;background:#10b981;border-radius:50%;animation:pulse-ring 2s ease-out infinite;"></div>
                <div style="width:8px;height:8px;background:#10b981;border-radius:50%;"></div>
            </div>
            <span style="color:#059669;font-size:0.75rem;font-weight:800;letter-spacing:0.8px;">LIVE</span>
        </div>
        <div style="background:#eef2ff;border:1px solid #c7d2fe;border-radius:30px;padding:5px 14px;">
            <span style="color:#4338ca;font-size:0.72rem;font-weight:700;">lablab.ai × Alpaca Hackathon 2026</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TRIGGER BUTTON (PROMINENT, IN MAIN BODY)
# ═══════════════════════════════════════════════════════════════════════════════
t_col1, t_col2, t_col3 = st.columns([1, 2, 1])
with t_col2:
    trigger_cycle = st.button("🚀  Run Full Agent Cycle Now", use_container_width=True)
    st.markdown("<div style='text-align:center; font-size:0.85rem; font-weight:800; color:#4338ca; margin-top:8px;'>💡 Note for Users: Results from the cycle will populate in the tabs below (Sentiment Log & Risk Gate Audit)</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE CYCLE EXECUTION (step-by-step real-time telemetry)
# ═══════════════════════════════════════════════════════════════════════════════
if trigger_cycle:
    st.markdown("---")
    st.markdown("#### ⚡ Live Pipeline Execution")
    progress_bar = st.progress(0)
    status_box = st.empty()
    live_log = st.container()

    try:
        portfolio  = PortfolioTracker()
        try:
            analyzer = SentimentAnalyzer()
        except ValueError as key_err:
            st.error(f"⚠️ API key not configured: {key_err}")
            st.info("Please set the `GEMINI_API_KEY` in your `.env` file or deployment environment variables.")
            st.stop()
        proposer   = TradeProposer()
        risk_gate  = RiskGate(portfolio)
        executor   = TradeExecutor(portfolio)
        monitor    = PositionMonitor(portfolio)

        # Step 0
        status_box.info("**[0/5]** 🔍 Scanning open positions for exit triggers...")
        progress_bar.progress(10)
        closed = monitor.run()
        with live_log:
            if closed:
                st.write(f"↳ Closed {closed} position(s) via take-profit/stop-loss/expiry rules.")
            else:
                st.write("↳ No open positions to evaluate.")
        time.sleep(0.3)

        # Step 1
        status_box.info("**[1/5]** 📰 Scraping live financial news via Google News RSS...")
        progress_bar.progress(25)
        news = fetch_news_for_watchlist(Config.WATCHLIST)
        total_arts = sum(len(v) for v in news.values())
        with live_log:
            st.write(f"↳ Fetched **{total_arts}** articles across **{len(news)}** tickers.")
        time.sleep(0.3)

        # Step 2
        status_box.info("**[2/5]** 🧠 Running NLP sentiment analysis on headlines...")
        progress_bar.progress(50)
        sentiments = analyzer.analyze_all(news)
        with live_log:
            if sentiments:
                for s in sentiments:
                    emoji = "🟢" if s["sentiment"]=="BULLISH" else ("🔴" if s["sentiment"]=="BEARISH" else "🟡")
                    st.write(f"↳ {emoji} **{s['ticker']}** → {s['sentiment']} ({float(s['confidence'])*100:.0f}%)")
            else:
                st.write("↳ No actionable signals this cycle.")
        time.sleep(0.3)

        # Step 3
        status_box.info("**[3/5]** 🎯 Selecting ATM option contracts from Alpaca chain...")
        progress_bar.progress(70)
        proposals = proposer.propose_all(sentiments) if sentiments else []
        with live_log:
            st.write(f"↳ Generated **{len(proposals)}** trade proposal(s).")
        time.sleep(0.3)

        # Step 4
        status_box.info("**[4/5]** 🛡️ Enforcing deterministic risk gate rules...")
        progress_bar.progress(85)
        approved_list, refused_list = [], []
        if proposals:
            approved_list, refused_list = risk_gate.approve_all(proposals)
        with live_log:
            st.write(f"↳ **{len(approved_list)}** approved, **{len(refused_list)}** refused by risk gate.")
        time.sleep(0.3)

        # Step 5
        status_box.info("**[5/5]** 📤 Submitting approved orders to Alpaca Paper Trading...")
        progress_bar.progress(95)
        if approved_list:
            executor.execute_all(approved_list)
            with live_log:
                st.write(f"↳ ✅ Executed **{len(approved_list)}** order(s)!")
        else:
            with live_log:
                st.write("↳ No trades to execute this cycle.")

        portfolio.snapshot()
        progress_bar.progress(100)
        status_box.success("✅ Full trading cycle completed successfully!")
        time.sleep(1.5)
        st.rerun()

    except Exception as exc:
        status_box.error(f"Pipeline error: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE PARAMETER CARDS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-bottom:16px;">
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;">Mode</div>
        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;margin-top:2px;">Paper Trading</div>
        <div style="font-size:0.68rem;color:#10b981;font-weight:600;margin-top:1px;">● Connected to Alpaca</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;">Watchlist</div>
        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;margin-top:2px;">{', '.join(Config.WATCHLIST)}</div>
        <div style="font-size:0.68rem;color:#6366f1;font-weight:600;margin-top:1px;">● {len(Config.WATCHLIST)} target equities</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;">Max Risk / Trade</div>
        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;margin-top:2px;">${Config.MAX_LOSS_PER_TRADE:,.0f}</div>
        <div style="font-size:0.68rem;color:#0ea5e9;font-weight:600;margin-top:1px;">● Hard-coded ceiling</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;">Auto-Exit Rules</div>
        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;margin-top:2px;">+{int(Config.TAKE_PROFIT_PCT*100)}% / -{int(Config.STOP_LOSS_PCT*100)}%</div>
        <div style="font-size:0.68rem;color:#f59e0b;font-weight:600;margin-top:1px;">● Take-profit & stop-loss</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="font-size:0.65rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;">Cycle Interval</div>
        <div style="font-size:0.92rem;font-weight:800;color:#0f172a;margin-top:2px;">Every 30 min</div>
        <div style="font-size:0.68rem;color:#8b5cf6;font-weight:600;margin-top:1px;">● Autonomous scheduling</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
trades         = read_trades()         or []
refused_trades = read_refused_trades() or []
sentiment_log  = read_sentiment_log()  or []
portfolio_hist = read_portfolio_history() or []

df_trades  = pd.DataFrame(trades)
df_refused = pd.DataFrame(refused_trades)
df_sent    = pd.DataFrame(sentiment_log)
df_port    = pd.DataFrame(portfolio_hist)

START_EQUITY   = 100_000

# Fetch live positions directly from Alpaca so it ALWAYS matches the CLI
from alpaca.trading.client import TradingClient
try:
    _live_client = TradingClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, paper=True)
    _live_acct = _live_client.get_account()
    _live_positions = _live_client.get_all_positions()
    cur_equity = float(_live_acct.portfolio_value)
    open_positions = len(_live_positions)
except Exception:
    cur_equity = START_EQUITY
    open_positions = 0
    _live_positions = []

total_pnl      = cur_equity - START_EQUITY
pnl_pct        = (total_pnl / START_EQUITY) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC CARDS
# ═══════════════════════════════════════════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💼 Portfolio Equity", f"${cur_equity:,.0f}")
c2.metric("📈 Net P&L",          f"${total_pnl:+,.0f}",   f"{pnl_pct:+.2f}%")
c3.metric("✅ Trades Executed",   len(trades))
c4.metric("🚫 Trades Refused",    len(refused_trades))
c5.metric("📋 Open Positions",    open_positions)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Sentiment Ticker Bar ─────────────────────────────────────────────────────
if not df_sent.empty and "ticker" in df_sent and "sentiment" in df_sent:
    latest = df_sent.drop_duplicates("ticker", keep="last").to_dict("records")
    def _sc(s): return {"BULLISH":"#059669","BEARISH":"#e11d48","NEUTRAL":"#d97706"}.get(s,"#475569")
    def _si(s): return {"BULLISH":"▲","BEARISH":"▼","NEUTRAL":"◆"}.get(s,"·")
    items = "".join([
        f'<span style="margin:0 22px;color:#cbd5e1">|</span>'
        f'<span style="color:#0f172a;font-weight:800;font-size:0.86rem;">{r["ticker"]}</span>'
        f'<span style="color:{_sc(r["sentiment"])};margin-left:5px;font-weight:800;font-size:0.86rem;">'
        f'{_si(r["sentiment"])} {r["sentiment"]}</span>'
        f'<span style="color:{_sc(r["sentiment"])};margin-left:4px;font-size:0.75rem;font-weight:700;">'
        f'{float(r.get("confidence",0))*100:.0f}%</span>'
        for r in latest
    ] * 3)
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px 0;overflow:hidden;
                margin-bottom:16px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.02);">
        <div style="display:inline-block;animation:ticker-scroll 24s linear infinite;padding:0 16px;
                    font-family:'JetBrains Mono',monospace;">{items}</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CHARTS ROW
# ═══════════════════════════════════════════════════════════════════════════════
col_chart, col_donut = st.columns([3, 1])

with col_chart:
    st.markdown('<div style="color:#475569;font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:6px;">◈ Portfolio Equity Curve</div>', unsafe_allow_html=True)
    if not df_port.empty and "equity" in df_port and "timestamp" in df_port:
        df_port["timestamp"] = pd.to_datetime(df_port["timestamp"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_port["timestamp"],y=df_port["equity"],fill="tozeroy",
            fillcolor="rgba(99,102,241,0.06)",line=dict(color="rgba(0,0,0,0)",width=0),showlegend=False,hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=df_port["timestamp"],y=df_port["equity"],mode="lines+markers",
            line=dict(color="#6366f1",width=2.5,shape="spline"),
            marker=dict(size=5,color="#06b6d4",line=dict(color="#fff",width=2)),
            hovertemplate="<b>$%{y:,.2f}</b><br>%{x}<extra></extra>"))
        fig.add_hline(y=START_EQUITY,line=dict(color="#cbd5e1",dash="dot",width=1.5),
            annotation_text="Base $100K",annotation_font=dict(color="#64748b",size=10))
        fig.update_layout(paper_bgcolor="#fff",plot_bgcolor="#fff",font=dict(color="#475569",family="Inter"),
            xaxis=dict(gridcolor="#f1f5f9",showgrid=True,zeroline=False),
            yaxis=dict(gridcolor="#f1f5f9",showgrid=True,zeroline=False,tickprefix="$"),
            height=240,margin=dict(l=10,r=10,t=8,b=10),showlegend=False,hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity history yet. Click **Run Full Agent Cycle Now** above to start trading.")

with col_donut:
    st.markdown('<div style="color:#475569;font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:6px;">◈ Signal Mix</div>', unsafe_allow_html=True)
    if not df_sent.empty and "sentiment" in df_sent:
        counts = df_sent["sentiment"].value_counts()
        cm = {"BULLISH":"#10b981","BEARISH":"#f43f5e","NEUTRAL":"#f59e0b"}
        fig2 = go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=0.66,
            marker_colors=[cm.get(l,"#94a3b8") for l in counts.index],textfont=dict(size=11,color="white"),
            hovertemplate="<b>%{label}</b>: %{value}<extra></extra>"))
        fig2.add_annotation(text=f"<b>{len(df_sent)}</b><br><span style='font-size:10px;color:#64748b'>signals</span>",
            x=0.5,y=0.5,showarrow=False,font=dict(size=14,color="#0f172a"))
        fig2.update_layout(paper_bgcolor="#fff",font=dict(color="#475569",family="Inter"),
            height=240,margin=dict(l=10,r=10,t=8,b=10),showlegend=True,
            legend=dict(font=dict(size=10,color="#475569"),orientation="h",x=0.5,xanchor="center",y=-0.15))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown("<div style='color:#94a3b8;padding:30px;font-size:0.82rem;'>No signals yet.</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_arch, tab_exec, tab_refused, tab_sentiment, tab_sandbox = st.tabs([
    "🏗️ Architecture & Pipeline",
    "⚡ Executed Trades",
    "🚫 Risk Gate Audit",
    "🧠 Sentiment Log",
    "🧪 Live AI Sandbox",
])

CL = dict(paper_bgcolor="#fff",plot_bgcolor="#fff",font=dict(color="#475569",family="Inter"),
    height=240,margin=dict(l=10,r=10,t=24,b=10),legend=dict(bgcolor="rgba(255,255,255,0.9)"),
    xaxis=dict(gridcolor="#f1f5f9"),yaxis=dict(gridcolor="#f1f5f9"))


# ── Tab: Architecture & Pipeline (HACKATHON JUDGES) ──────────────────────────
with tab_arch:
    st.markdown("### 🏗️ System Architecture & NLP Pipeline")
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">
        <div style="font-size:1.05rem;font-weight:800;color:#0f172a;margin-bottom:12px;">What is Sentinel Options?</div>
        <div style="color:#334155;font-size:0.88rem;line-height:1.7;">
            <b>Sentinel Options</b> is a fully autonomous AI-powered options trading agent built for the
            <b>Alpaca AI Trading Agents Hackathon</b> (lablab.ai × Alpaca, Aug 28 – Sep 4, 2026).
            It ingests real-time financial news, extracts actionable sentiment signals using a large language model,
            proposes ATM option contracts via the Alpaca Trading API, enforces strict deterministic risk gates
            (no AI in the risk layer), and executes paper trades — all without human intervention.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline Diagram
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">
        <div style="font-size:0.9rem;font-weight:800;color:#0f172a;margin-bottom:16px;">6-Stage Autonomous Pipeline (runs every 30 minutes)</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;">
            <div style="background:linear-gradient(135deg,#ede9fe,#ddd6fe);border:1px solid #c4b5fd;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">🔍</div>
                <div style="font-size:0.72rem;font-weight:700;color:#4c1d95;">STEP 0</div>
                <div style="font-size:0.78rem;font-weight:600;color:#5b21b6;">Position<br>Monitor</div>
            </div>
            <div style="color:#94a3b8;font-size:1.2rem;font-weight:300;">→</div>
            <div style="background:linear-gradient(135deg,#dbeafe,#bfdbfe);border:1px solid #93c5fd;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">📰</div>
                <div style="font-size:0.72rem;font-weight:700;color:#1e3a5f;">STEP 1</div>
                <div style="font-size:0.78rem;font-weight:600;color:#1d4ed8;">News<br>Scraper</div>
            </div>
            <div style="color:#94a3b8;font-size:1.2rem;font-weight:300;">→</div>
            <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border:1px solid #fbbf24;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">🧠</div>
                <div style="font-size:0.72rem;font-weight:700;color:#78350f;">STEP 2</div>
                <div style="font-size:0.78rem;font-weight:600;color:#b45309;">NLP Sentiment<br>Analyzer</div>
            </div>
            <div style="color:#94a3b8;font-size:1.2rem;font-weight:300;">→</div>
            <div style="background:linear-gradient(135deg,#ccfbf1,#99f6e4);border:1px solid #5eead4;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">🎯</div>
                <div style="font-size:0.72rem;font-weight:700;color:#134e4a;">STEP 3</div>
                <div style="font-size:0.78rem;font-weight:600;color:#0d9488;">Trade<br>Proposer</div>
            </div>
            <div style="color:#94a3b8;font-size:1.2rem;font-weight:300;">→</div>
            <div style="background:linear-gradient(135deg,#fee2e2,#fecaca);border:1px solid #fca5a5;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">🛡️</div>
                <div style="font-size:0.72rem;font-weight:700;color:#7f1d1d;">STEP 4</div>
                <div style="font-size:0.78rem;font-weight:600;color:#dc2626;">Risk<br>Gate</div>
            </div>
            <div style="color:#94a3b8;font-size:1.2rem;font-weight:300;">→</div>
            <div style="background:linear-gradient(135deg,#d1fae5,#a7f3d0);border:1px solid #6ee7b7;border-radius:10px;padding:10px 16px;text-align:center;">
                <div style="font-size:1.1rem;">🚀</div>
                <div style="font-size:0.72rem;font-weight:700;color:#064e3b;">STEP 5</div>
                <div style="font-size:0.78rem;font-weight:600;color:#059669;">Alpaca<br>Executor</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key Architecture Cards
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,0.02);height:100%;">
            <div style="font-size:0.85rem;font-weight:800;color:#4338ca;margin-bottom:8px;">🧠 NLP Sentiment Layer</div>
            <ul style="color:#334155;font-size:0.8rem;line-height:1.8;padding-left:16px;margin:0;">
                <li>Scrapes <b>Google News RSS</b> for each ticker</li>
                <li>Sends headlines to LLM with structured JSON prompt</li>
                <li>Outputs: <code>BULLISH</code> / <code>BEARISH</code> / <code>NEUTRAL</code></li>
                <li>Includes <b>confidence score</b> (0.0–1.0) and reasoning</li>
                <li>Minimum confidence threshold: <b>0.65</b> for trade</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,0.02);height:100%;">
            <div style="font-size:0.85rem;font-weight:800;color:#dc2626;margin-bottom:8px;">🛡️ Deterministic Risk Gate</div>
            <ul style="color:#334155;font-size:0.8rem;line-height:1.8;padding-left:16px;margin:0;">
                <li><b>No AI in risk layer</b> — pure mathematical rules</li>
                <li>Market hours enforcement (9:30–15:30 ET)</li>
                <li>Max $2,000 cost per trade</li>
                <li>Max 8 concurrent positions</li>
                <li>Daily loss limit: $8,000</li>
                <li>Single-ticker concentration cap: 25%</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown("""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px;box-shadow:0 1px 4px rgba(0,0,0,0.02);height:100%;">
            <div style="font-size:0.85rem;font-weight:800;color:#059669;margin-bottom:8px;">📊 Trade Execution & Lifecycle</div>
            <ul style="color:#334155;font-size:0.8rem;line-height:1.8;padding-left:16px;margin:0;">
                <li><b>Alpaca Trading API</b> (Paper mode, $100K)</li>
                <li>Selects ATM options, 7–45 DTE window</li>
                <li>Auto take-profit at <b>+50%</b></li>
                <li>Auto stop-loss at <b>-40%</b></li>
                <li>Auto-close at ≤3 DTE</li>
                <li>Full audit trail in JSON logs</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Tech Stack
    st.markdown("""
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px 24px;box-shadow:0 2px 8px rgba(0,0,0,0.03);">
        <div style="font-size:0.9rem;font-weight:800;color:#0f172a;margin-bottom:12px;">⚙️ Technology Stack</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;">
            <span style="background:#eef2ff;color:#4338ca;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Python 3.11</span>
            <span style="background:#ecfdf5;color:#059669;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Alpaca Trading API</span>
            <span style="background:#ecfdf5;color:#059669;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Alpaca Market Data API</span>
            <span style="background:#fef3c7;color:#b45309;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">LLM Sentiment Engine</span>
            <span style="background:#fee2e2;color:#dc2626;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Deterministic Risk Gate</span>
            <span style="background:#f1f5f9;color:#475569;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Streamlit Dashboard</span>
            <span style="background:#f1f5f9;color:#475569;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Google News RSS</span>
            <span style="background:#ede9fe;color:#6d28d9;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Railway (Deployment)</span>
            <span style="background:#f1f5f9;color:#475569;padding:5px 12px;border-radius:20px;font-size:0.75rem;font-weight:700;">Plotly Charts</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Tab: Executed Trades ──────────────────────────────────────────────────────
with tab_exec:
    if df_trades.empty:
        st.markdown("""<div style="padding:36px;text-align:center;background:#fff;border:1px solid #e2e8f0;border-radius:12px;">
            <div style="font-size:2rem;margin-bottom:8px;">📭</div>
            <div style="font-weight:700;color:#0f172a;">No trades executed yet</div>
            <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">Trades execute during market hours (9:30–15:30 ET) when signals pass the risk gate.</div>
        </div>""", unsafe_allow_html=True)
    else:
        cols = [c for c in ["timestamp","ticker","option_type","symbol","strike","contracts","mid_price","estimated_cost","status"] if c in df_trades]
        disp = df_trades[cols].sort_values("timestamp",ascending=False) if "timestamp" in df_trades else df_trades[cols]
        disp = disp.rename(columns={"timestamp":"Time","option_type":"Type","mid_price":"Fill $","estimated_cost":"Cost $"})
        st.dataframe(disp, use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.markdown("#### 🟢 Live Open Positions (Direct from Alpaca)")
    if not _live_positions:
        st.info("No open positions currently held in Alpaca.")
    else:
        pos_data = []
        for p in _live_positions:
            pos_data.append({
                "Symbol": p.symbol,
                "Qty": int(p.qty),
                "Avg Cost": f"${float(p.avg_entry_price):.2f}",
                "Current Value": f"${float(p.market_value):.2f}",
                "Unrealized P&L": f"${float(p.unrealized_pl):.2f}"
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)


# ── Tab: Refused Trades ───────────────────────────────────────────────────────
with tab_refused:
    if df_refused.empty:
        st.markdown("""<div style="padding:36px;text-align:center;background:#fff;border:1px solid #e2e8f0;border-radius:12px;">
            <div style="font-size:2rem;margin-bottom:8px;">🛡️</div>
            <div style="font-weight:700;color:#0f172a;">No refusals recorded</div>
            <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">Refusals appear when the deterministic risk gate blocks a proposed trade.</div>
        </div>""", unsafe_allow_html=True)
    else:
        c_l, c_r = st.columns([3,2])
        with c_l:
            cols = [c for c in ["timestamp","ticker","option_type","reason"] if c in df_refused]
            disp = df_refused[cols].sort_values("timestamp",ascending=False) if "timestamp" in df_refused else df_refused[cols]
            st.dataframe(disp, use_container_width=True, hide_index=True)
        with c_r:
            if "reason" in df_refused.columns:
                rc = df_refused["reason"].str.split("(").str[0].str.strip().value_counts().reset_index()
                rc.columns = ["Reason","Count"]
                fig4 = go.Figure(go.Bar(x=rc["Count"],y=rc["Reason"],orientation="h",
                    marker=dict(color=rc["Count"],colorscale=[[0,"#6366f1"],[1,"#f43f5e"]])))
                fig4.update_layout(**CL, title="Refusal Breakdown")
                st.plotly_chart(fig4, use_container_width=True)


# ── Tab: Sentiment Log ────────────────────────────────────────────────────────
with tab_sentiment:
    if df_sent.empty:
        st.markdown("""<div style="padding:36px;text-align:center;background:#fff;border:1px solid #e2e8f0;border-radius:12px;">
            <div style="font-size:2rem;margin-bottom:8px;">🧠</div>
            <div style="font-weight:700;color:#0f172a;">No sentiment records yet</div>
        </div>""", unsafe_allow_html=True)
    else:
        c_s, c_b = st.columns([3,2])
        with c_s:
            cols = [c for c in ["timestamp","ticker","sentiment","confidence","suggested_trade","reasoning"] if c in df_sent]
            disp = df_sent[cols].sort_values("timestamp",ascending=False) if "timestamp" in df_sent else df_sent[cols]
            def _cs(v):
                return {"BULLISH":"color:#059669;font-weight:800","BEARISH":"color:#e11d48;font-weight:800","NEUTRAL":"color:#d97706;font-weight:800"}.get(v,"")
            st.dataframe(disp.style.map(_cs,subset=["sentiment"] if "sentiment" in disp else []),
                         use_container_width=True, hide_index=True)
        with c_b:
            if "sentiment" in df_sent and "ticker" in df_sent:
                pivot = df_sent.groupby(["ticker","sentiment"]).size().reset_index(name="n")
                fig5 = px.bar(pivot,x="ticker",y="n",color="sentiment",
                    color_discrete_map={"BULLISH":"#10b981","BEARISH":"#f43f5e","NEUTRAL":"#f59e0b"},barmode="group")
                fig5.update_layout(**CL, title="Signals by Ticker")
                st.plotly_chart(fig5, use_container_width=True)


# ── Tab: AI Sandbox ───────────────────────────────────────────────────────────
with tab_sandbox:
    st.markdown("##### 🧪 On-Demand Ticker Analysis")
    st.caption("Test the full pipeline on any ticker — fetch news, run NLP, propose option, check risk gate.")
    sb1, sb2 = st.columns([1,2])
    with sb1:
        test_ticker = st.text_input("Ticker Symbol", value="NVDA").upper().strip()
        num_news = st.slider("Headlines to fetch", 3, 15, 7)
        run_btn = st.button("🔍 Analyze & Propose", use_container_width=True)
    with sb2:
        if run_btn and test_ticker:
            sp = st.empty()
            pb = st.progress(10)
            sp.info(f"**1/3** Scraping news for `{test_ticker}`...")
            fetcher = NewsFetcher()
            articles = fetcher.fetch(test_ticker, max_results=num_news)
            pb.progress(40)
            sp.info(f"**2/3** Running NLP inference for `{test_ticker}`...")
            try:
                analyzer = SentimentAnalyzer()
            except ValueError as key_err:
                pb.empty()
                sp.empty()
                st.error(f"⚠️ API key not configured: {key_err}")
                st.info("Please set the `GEMINI_API_KEY` in your `.env` file or deployment environment variables.")
                st.stop()
            signal = analyzer.analyze(test_ticker, articles)
            pb.progress(75)
            sp.info(f"**3/3** Checking option chain & risk gate...")
            proposer = TradeProposer()
            pb.progress(100)
            sp.empty()
            st.write(f"📰 Analyzed **{len(articles)}** articles for **{test_ticker}**")
            if signal:
                sent = signal.get("sentiment","NEUTRAL")
                conf = float(signal.get("confidence",0))
                trade = signal.get("suggested_trade")
                reasoning = signal.get("reasoning","")
                color = "#059669" if sent=="BULLISH" else ("#e11d48" if sent=="BEARISH" else "#d97706")
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:8px 0;box-shadow:0 2px 8px rgba(0,0,0,0.03);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:1.15rem;font-weight:800;color:#0f172a;">{test_ticker}</span>
                        <span style="font-size:0.95rem;font-weight:800;color:{color};">{sent} ({conf*100:.0f}%)</span>
                    </div>
                    <div style="font-size:0.84rem;color:#334155;margin-top:6px;line-height:1.5;"><b>Reasoning:</b> {reasoning}</div>
                    <div style="font-size:0.84rem;color:#4f46e5;font-weight:700;margin-top:6px;"><b>Trade Signal:</b> {trade or 'None'}</div>
                </div>""", unsafe_allow_html=True)
                if trade:
                    prop = proposer.propose(signal)
                    if prop:
                        st.json(prop)
                        portfolio_t = PortfolioTracker()
                        gate = RiskGate(portfolio_t)
                        ok, reason = gate.approve(prop)
                        if ok:
                            st.success("✅ **Risk Gate PASSED** — would execute live!")
                        else:
                            st.warning(f"❌ **Risk Gate REFUSED**: {reason}")
                    else:
                        st.info("No ATM contract found in 7–45 DTE range.")
            else:
                st.error("Sentiment analysis returned no result.")


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="border-top:1px solid #e2e8f0;padding-top:14px;display:flex;align-items:center;justify-content:space-between;
            color:#94a3b8;font-size:0.73rem;">
    <div>⚡ <b>Sentinel Options</b> — Autonomous AI Options Trading Agent</div>
    <div style="font-family:'JetBrains Mono',monospace;">NLP Pipeline → Option Proposer → Deterministic Risk Gate → Alpaca Executor</div>
    <div>Alpaca × lablab.ai Hackathon 2026</div>
</div>
""", unsafe_allow_html=True)

# ── Auto-Refresh ──────────────────────────────────────────────────────────────
time.sleep(60)
st.rerun()
