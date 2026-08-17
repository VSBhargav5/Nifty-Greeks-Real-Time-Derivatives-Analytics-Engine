"""Streamlit dashboard — trading-terminal look for Nifty Greeks / GEX."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

from metrics import (
    atm_iv,
    gamma_flip_strike,
    gamma_regime,
    iv_skew,
    max_pain,
    oi_walls,
    put_call_ratio,
)

st.set_page_config(
    page_title="Nifty Greeks Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Dark trading-terminal chrome ---
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"]  {
  font-family: 'Space Grotesk', sans-serif;
}
.stApp {
  background: radial-gradient(1200px 600px at 10% -10%, #1a2744 0%, #0b0f19 45%, #070a12 100%);
  color: #e8eefc;
}
header[data-testid="stHeader"] { background: rgba(0,0,0,0); }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }

.hero {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem;
  margin-bottom: 0.6rem;
}
.hero h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.1rem; font-weight: 700; margin: 0;
  background: linear-gradient(90deg, #7dd3fc, #a78bfa, #f472b6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero .sub { color: #94a3b8; font-size: 0.92rem; margin-top: 0.25rem; }

.regime {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem; font-weight: 600;
  padding: 0.55rem 0.9rem; border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.7);
  white-space: nowrap;
}
.regime.long { color: #4ade80; border-color: rgba(74,222,128,0.35); box-shadow: 0 0 24px rgba(74,222,128,0.12); }
.regime.short { color: #f87171; border-color: rgba(248,113,113,0.35); box-shadow: 0 0 24px rgba(248,113,113,0.12); }
.regime.neutral { color: #fbbf24; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin: 0.9rem 0 1.1rem 0;
}
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.kpi {
  background: linear-gradient(160deg, rgba(30,41,59,0.9), rgba(15,23,42,0.85));
  border: 1px solid rgba(148,163,184,0.14);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  box-shadow: 0 8px 28px rgba(0,0,0,0.25);
}
.kpi .label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: #94a3b8; margin-bottom: 0.35rem;
}
.kpi .value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.35rem; font-weight: 700; color: #f8fafc;
}
.kpi .hint { font-size: 0.75rem; color: #64748b; margin-top: 0.2rem; }

.stTabs [data-baseweb="tab-list"] {
  gap: 0.4rem; background: transparent; border-bottom: 1px solid rgba(148,163,184,0.15);
}
.stTabs [data-baseweb="tab"] {
  background: rgba(15,23,42,0.5); border-radius: 10px 10px 0 0;
  color: #94a3b8; padding: 0.55rem 1rem;
}
.stTabs [aria-selected="true"] {
  background: rgba(56,189,248,0.12) !important; color: #7dd3fc !important;
}
div[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; }
</style>
""",
    unsafe_allow_html=True,
)

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,23,42,0.35)",
    font=dict(family="JetBrains Mono, monospace", size=11, color="#cbd5e1"),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)
engine = create_engine(DB_URL)

LATEST_SQL = """
SELECT * FROM nifty_greeks_realtime
WHERE ingestion_timestamp = (SELECT MAX(ingestion_timestamp) FROM nifty_greeks_realtime)
"""
HISTORY_SQL = """
SELECT
    ingestion_timestamp,
    MAX(underlying) AS spot,
    SUM(gex) AS net_gex
FROM nifty_greeks_realtime
GROUP BY ingestion_timestamp
ORDER BY ingestion_timestamp DESC
LIMIT 48
"""


def _add_level(fig: go.Figure, x: float | None, label: str, color: str) -> None:
    if x is None:
        return
    fig.add_vline(
        x=x,
        line_dash="dot",
        line_color=color,
        line_width=1.4,
        annotation_text=label,
        annotation_position="top",
        annotation_font_size=10,
        annotation_font_color=color,
    )


def style_fig(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=14)), **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.12)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)", zeroline=False)
    return fig


try:
    df = pd.read_sql(LATEST_SQL, engine)
except Exception:
    st.error("Waiting for ETL… run `python etl.py --once` or `docker compose up etl`.")
    st.stop()

if df.empty:
    st.warning("Table empty — wait for the first ETL cycle.")
    st.stop()

expiries = sorted(df["expiry"].dropna().unique().tolist()) if "expiry" in df.columns else []
if len(expiries) > 1:
    chosen = st.selectbox("Expiry", expiries, index=0)
    df = df[df["expiry"] == chosen].copy()

spot = float(df["underlying"].iloc[0])
latest = pd.to_datetime(df["ingestion_timestamp"].iloc[0])
expiry = str(df["expiry"].iloc[0]) if "expiry" in df.columns else "—"
pain = max_pain(df)
net_gex = float(df["gex"].sum()) if "gex" in df.columns else None
pcr = put_call_ratio(df)
atm = atm_iv(df, spot)
skew = iv_skew(df, spot)
walls = oi_walls(df)
flip = gamma_flip_strike(df) if "gex" in df.columns else None
regime = gamma_regime(net_gex)
regime_cls = "long" if net_gex and net_gex > 0 else ("short" if net_gex and net_gex < 0 else "neutral")

# --- Hero ---
st.markdown(
    f"""
<div class="hero">
  <div>
    <h1>⚡ Nifty Greeks Engine</h1>
    <div class="sub">NSE chain → vectorized BS Greeks → Postgres → live GEX terminal</div>
  </div>
  <div class="regime {regime_cls}">{regime}</div>
</div>
""",
    unsafe_allow_html=True,
)

ctrl1, ctrl2, ctrl3 = st.columns([1, 2, 2])
with ctrl1:
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()
with ctrl2:
    strike_window = st.slider("Strike window ± spot", 300, 1500, 600, step=100)
with ctrl3:
    auto_sec = st.selectbox("Auto-refresh", [0, 30, 60, 120], format_func=lambda s: "Off" if s == 0 else f"{s}s")
    if auto_sec:
        st.markdown(f"<meta http-equiv='refresh' content='{auto_sec}'>", unsafe_allow_html=True)

# --- KPI cards ---
st.markdown(
    f"""
<div class="kpi-grid">
  <div class="kpi"><div class="label">Spot</div><div class="value">{spot:,.2f}</div><div class="hint">as of {latest.strftime('%H:%M:%S')}</div></div>
  <div class="kpi"><div class="label">Expiry</div><div class="value">{expiry[:11]}</div><div class="hint">nearest selected</div></div>
  <div class="kpi"><div class="label">Max pain</div><div class="value">{f"{pain:,.0f}" if pain else "—"}</div><div class="hint">OI-weighted</div></div>
  <div class="kpi"><div class="label">Net GEX</div><div class="value">{f"{net_gex/1e6:,.2f}M" if net_gex is not None else "—"}</div><div class="hint">dealer proxy</div></div>
  <div class="kpi"><div class="label">PCR (OI)</div><div class="value">{f"{pcr:.2f}" if pcr is not None else "—"}</div><div class="hint">puts / calls</div></div>
  <div class="kpi"><div class="label">ATM IV</div><div class="value">{f"{atm*100:.1f}%" if atm is not None else "—"}</div><div class="hint">near-spot avg</div></div>
  <div class="kpi"><div class="label">IV skew</div><div class="value">{f"{skew*100:+.1f}pp" if skew is not None else "—"}</div><div class="hint">put wing − call wing</div></div>
  <div class="kpi"><div class="label">Walls / flip</div><div class="value" style="font-size:1.05rem">{(f"↑{walls['call_resistance']:,.0f}" if walls['call_resistance'] else "↑—")} · {(f"↓{walls['put_support']:,.0f}" if walls['put_support'] else "↓—")}</div><div class="hint">γ flip ≈ {f"{flip:,.0f}" if flip else "—"}</div></div>
</div>
""",
    unsafe_allow_html=True,
)

df_near = df[(df["strike"] > spot - strike_window) & (df["strike"] < spot + strike_window)].copy()

tab_oi, tab_gex, tab_hist, tab_data = st.tabs(["📈 OI & IV", "☢️ GEX map", "⏱ History", "📋 Data"])

with tab_oi:
    c1, c2 = st.columns(2)
    with c1:
        fig_oi = px.bar(
            df_near,
            x="strike",
            y="oi",
            color="type",
            barmode="group",
            color_discrete_map={"CE": "#f87171", "PE": "#4ade80"},
        )
        style_fig(fig_oi, f"Open interest (±{strike_window})")
        _add_level(fig_oi, spot, "spot", "#38bdf8")
        _add_level(fig_oi, walls.get("call_resistance"), "call wall", "#f87171")
        _add_level(fig_oi, walls.get("put_support"), "put wall", "#4ade80")
        st.plotly_chart(fig_oi, use_container_width=True)
    with c2:
        fig_iv = px.line(
            df_near,
            x="strike",
            y="iv",
            color="type",
            markers=True,
            color_discrete_map={"CE": "#f87171", "PE": "#4ade80"},
        )
        style_fig(fig_iv, "Volatility smile")
        _add_level(fig_iv, spot, "spot", "#38bdf8")
        st.plotly_chart(fig_iv, use_container_width=True)

    if "change_in_oi" in df.columns:
        fig_coi = px.bar(
            df_near,
            x="strike",
            y="change_in_oi",
            color="type",
            barmode="relative",
            color_discrete_map={"CE": "#f87171", "PE": "#4ade80"},
        )
        style_fig(fig_coi, "Change in OI — fresh positioning")
        _add_level(fig_coi, spot, "spot", "#38bdf8")
        st.plotly_chart(fig_coi, use_container_width=True)

with tab_gex:
    if "gex" not in df.columns:
        from metrics import dealer_gex

        df["gex"] = dealer_gex(df["gamma"], df["oi"], df["type"])

    by_strike = (
        df[(df["strike"] > spot - strike_window - 100) & (df["strike"] < spot + strike_window + 100)]
        .groupby("strike", as_index=False)["gex"]
        .sum()
        .sort_values("strike")
    )
    colors = ["#4ade80" if v >= 0 else "#f87171" for v in by_strike["gex"]]
    fig_gex = go.Figure(
        go.Bar(
            x=by_strike["strike"],
            y=by_strike["gex"],
            marker_color=colors,
            name="Net GEX",
        )
    )
    style_fig(fig_gex, "Net gamma exposure by strike")
    _add_level(fig_gex, spot, "spot", "#38bdf8")
    _add_level(fig_gex, pain, "max pain", "#c084fc")
    _add_level(fig_gex, flip, "γ flip", "#fbbf24")
    st.plotly_chart(fig_gex, use_container_width=True)

    # Cumulative GEX profile
    if not by_strike.empty:
        cum = by_strike.copy()
        cum["cum_gex"] = cum["gex"].cumsum()
        fig_cum = go.Figure(
            go.Scatter(
                x=cum["strike"],
                y=cum["cum_gex"],
                mode="lines+markers",
                line=dict(color="#a78bfa", width=2.5),
                marker=dict(size=5),
                fill="tozeroy",
                fillcolor="rgba(167,139,250,0.15)",
            )
        )
        style_fig(fig_cum, "Cumulative GEX profile")
        _add_level(fig_cum, flip, "γ flip", "#fbbf24")
        _add_level(fig_cum, spot, "spot", "#38bdf8")
        st.plotly_chart(fig_cum, use_container_width=True)

with tab_hist:
    try:
        hist = pd.read_sql(HISTORY_SQL, engine)
    except Exception:
        hist = pd.DataFrame()
    if not hist.empty and len(hist) > 1:
        hist = hist.sort_values("ingestion_timestamp")
        h1, h2 = st.columns(2)
        with h1:
            fig_spot = px.line(hist, x="ingestion_timestamp", y="spot", markers=True)
            fig_spot.update_traces(line_color="#38bdf8")
            style_fig(fig_spot, "Spot path")
            st.plotly_chart(fig_spot, use_container_width=True)
        with h2:
            fig_ng = px.line(hist, x="ingestion_timestamp", y="net_gex", markers=True)
            fig_ng.update_traces(line_color="#a78bfa")
            style_fig(fig_ng, "Net GEX path")
            st.plotly_chart(fig_ng, use_container_width=True)
    else:
        st.info("History needs at least two ETL snapshots.")

with tab_data:
    show_cols = [
        c
        for c in [
            "expiry",
            "type",
            "strike",
            "premium",
            "oi",
            "change_in_oi",
            "volume",
            "iv",
            "delta",
            "gamma",
            "theta",
            "vega",
            "gex",
        ]
        if c in df.columns
    ]
    view = df[show_cols].sort_values(["expiry", "strike"] if "expiry" in show_cols else ["strike"])
    st.dataframe(view, use_container_width=True, height=440)
    st.download_button(
        "⬇ Download snapshot CSV",
        data=view.to_csv(index=False),
        file_name=f"greeks_{latest.strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
