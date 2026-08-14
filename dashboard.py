"""Streamlit dashboard for latest Nifty Greeks / GEX snapshot + history."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

from metrics import max_pain

st.set_page_config(page_title="Nifty Greeks Engine", layout="wide")

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)
engine = create_engine(DB_URL)

st.title("⚡ Nifty 50: Real-Time Gamma Exposure & Greeks")
st.caption("NSE option chain → vectorized Greeks → PostgreSQL → Streamlit")

if st.button("Refresh data"):
    st.rerun()

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

try:
    df = pd.read_sql(LATEST_SQL, engine)
except Exception:
    st.error("Waiting for ETL to populate data… Start `python etl.py` or `docker compose up etl`.")
    st.stop()

if df.empty:
    st.warning("Table exists but is empty. Wait for the first ETL cycle.")
    st.stop()

spot = float(df["underlying"].iloc[0])
latest = pd.to_datetime(df["ingestion_timestamp"].iloc[0])
pain = max_pain(df)
net_gex = float(df["gex"].sum()) if "gex" in df.columns else None

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY spot", f"{spot:,.2f}")
m2.metric("Last update", latest.strftime("%H:%M:%S"))
m3.metric("Max pain", f"{pain:,.0f}" if pain else "—")
m4.metric("Net GEX", f"{net_gex:,.0f}" if net_gex is not None else "—")

df_near = df[(df["strike"] > spot - 500) & (df["strike"] < spot + 500)]

col1, col2 = st.columns(2)
with col1:
    st.subheader("Open Interest")
    fig_oi = px.bar(
        df_near,
        x="strike",
        y="oi",
        color="type",
        barmode="group",
        color_discrete_map={"CE": "#e74c3c", "PE": "#27ae60"},
        title="OI near spot (±500)",
    )
    st.plotly_chart(fig_oi, use_container_width=True)

with col2:
    st.subheader("Implied Volatility Smile")
    fig_iv = px.line(
        df_near,
        x="strike",
        y="iv",
        color="type",
        markers=True,
        title="IV by strike",
    )
    st.plotly_chart(fig_iv, use_container_width=True)

st.subheader("Net Gamma Exposure (dealer positioning proxy)")
if "gex" not in df.columns:
    from metrics import dealer_gex

    df["gex"] = dealer_gex(df["gamma"], df["oi"], df["type"])

df_gex = df[(df["strike"] > spot - 600) & (df["strike"] < spot + 600)]
fig_gex = px.bar(
    df_gex,
    x="strike",
    y="gex",
    color="gex",
    color_continuous_scale=px.colors.diverging.RdYlGn,
    title="Positive GEX ≈ dealer long gamma",
)
st.plotly_chart(fig_gex, use_container_width=True)

st.subheader("Intraday history (last snapshots)")
try:
    hist = pd.read_sql(HISTORY_SQL, engine)
except Exception:
    hist = pd.DataFrame()

if not hist.empty and len(hist) > 1:
    hist = hist.sort_values("ingestion_timestamp")
    h1, h2 = st.columns(2)
    with h1:
        fig_spot = px.line(hist, x="ingestion_timestamp", y="spot", markers=True, title="Spot over time")
        st.plotly_chart(fig_spot, use_container_width=True)
    with h2:
        fig_ng = px.line(hist, x="ingestion_timestamp", y="net_gex", markers=True, title="Net GEX over time")
        st.plotly_chart(fig_ng, use_container_width=True)
else:
    st.info("History charts appear after at least two ETL snapshots.")

st.markdown("---")
st.write("### Latest snapshot (sample)")
show_cols = [c for c in ["type", "strike", "premium", "oi", "iv", "delta", "gamma", "gex"] if c in df.columns]
st.dataframe(df[show_cols].head(20), use_container_width=True)
