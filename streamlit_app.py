"""
streamlit_app.py – Combined entry point for Render deployment.

Starts the trading agent in a background thread and serves the
Streamlit dashboard. All data files stay on the same filesystem.
"""
import os
import sys
import threading
import time

import streamlit as st

# ── Start the agent in a background thread (once per process) ─────────────────
_AGENT_STARTED = False
_agent_lock    = threading.Lock()


def _run_agent():
    """Blocking call to the agent's main loop."""
    # Add project root to path so imports resolve
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from src.agent_controller import AgentController
        controller = AgentController()
        controller.start()
    except Exception as exc:
        print(f"[agent-thread] crashed: {exc}", flush=True)


def _ensure_agent_running():
    global _AGENT_STARTED
    with _agent_lock:
        if not _AGENT_STARTED:
            t = threading.Thread(target=_run_agent, daemon=True, name="agent")
            t.start()
            _AGENT_STARTED = True
            print("[streamlit_app] Agent thread started.", flush=True)


_ensure_agent_running()

# ── Hand off to the actual dashboard ─────────────────────────────────────────
# Import all dashboard code in-place so Streamlit renders it normally.
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "dashboard.py")
with open(dashboard_path, "r", encoding="utf-8") as _f:
    exec(compile(_f.read(), dashboard_path, "exec"), {"__file__": dashboard_path})
