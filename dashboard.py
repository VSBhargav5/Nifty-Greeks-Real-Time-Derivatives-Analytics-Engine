"""Streamlit dashboard for latest Nifty Greeks / GEX snapshot."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

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


def _max_pain(df: pd.DataFrame) -> float | None:
    """Strike that minimizes total option buyer loss (classic OI max-pain)."""
    strikes = sorted(df["strike"].unique())
    if not len(strikes):
        return None
    best_strike, best_pain = None, float("inf")
    for s in strikes:
        call_pain = (
            df[(df["type"] == "CE") & (df["strike"] < s)]["oi"]
            * (s - df[(df["type"] == "CE") & (df["strike"] < s)]["strike"])
        ).sum()
        put_pain = (
            df[(df["type"] == "PE") & (df["strike"] > s)]["oi"]
            * (df[(df["type"] == "PE") & (df["strike"] > s)]["strike"] - s)
        ).sum()
        total = float(call_pain + put_pain)
        if total < best_pain:
            best_pain = total
            best_strike = float(s)
    return best_strike


query = """
SELECT * FROM nifty_greeks_realtime
WHERE ingestion_timestamp = (SELECT MAX(ingestion_timestamp) FROM nifty_greeks_realtime)
"""

try:
    df = pd.read_sql(query, engine)
except Exception:
    st.error("Waiting for ETL to populate data… Start `python etl.py` after Postgres is up.")
    st.stop()

if df.empty:
    st.warning("Table exists but is empty. Wait for the first ETL cycle.")
    st.stop()

spot = float(df["underlying"].iloc[0])
latest = pd.to_datetime(df["ingestion_timestamp"].iloc[0])
max_pain = _max_pain(df)
net_gex = float(df["gex"].sum()) if "gex" in df.columns else None

m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY spot", f"{spot:,.2f}")
m2.metric("Last update", latest.strftime("%H:%M:%S"))
m3.metric("Max pain", f"{max_pain:,.0f}" if max_pain else "—")
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
    df["gex"] = df.apply(
        lambda r: r["gamma"] * r["oi"] * 100 if r["type"] == "CE" else -r["gamma"] * r["oi"] * 100,
        axis=1,
    )

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

st.markdown("---")
st.write("### Latest snapshot (sample)")
show_cols = [c for c in ["type", "strike", "premium", "oi", "iv", "delta", "gamma", "gex"] if c in df.columns]
st.dataframe(df[show_cols].head(20), use_container_width=True)
