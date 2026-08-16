"""Streamlit dashboard for latest Nifty Greeks / GEX snapshot + history."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

from metrics import atm_iv, gamma_flip_strike, max_pain, oi_walls, put_call_ratio

st.set_page_config(page_title="Nifty Greeks Engine", layout="wide")

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)
engine = create_engine(DB_URL)

st.title("⚡ Nifty Greeks Engine")
st.caption("NSE option chain → vectorized Greeks → PostgreSQL → Streamlit")

ctrl1, ctrl2, ctrl3 = st.columns([1, 2, 2])
with ctrl1:
    if st.button("Refresh"):
        st.rerun()
with ctrl2:
    strike_window = st.slider("Strike window ±spot", 300, 1500, 500, step=100)
with ctrl3:
    auto_sec = st.selectbox("Auto-refresh (seconds)", [0, 30, 60, 120], index=0)
    if auto_sec:
        st.caption(f"Page will rerun about every {auto_sec}s")
        st.markdown(
            f"<meta http-equiv='refresh' content='{auto_sec}'>",
            unsafe_allow_html=True,
        )

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
    st.error("Waiting for ETL… `python etl.py --once` or `docker compose up etl`.")
    st.stop()

if df.empty:
    st.warning("Table empty — wait for the first ETL cycle.")
    st.stop()

# Optional: filter to one expiry if multiple present
expiries = sorted(df["expiry"].dropna().unique().tolist()) if "expiry" in df.columns else []
if len(expiries) > 1:
    chosen = st.selectbox("Expiry", expiries, index=0)
    df = df[df["expiry"] == chosen].copy()

spot = float(df["underlying"].iloc[0])
latest = pd.to_datetime(df["ingestion_timestamp"].iloc[0])
expiry = df["expiry"].iloc[0] if "expiry" in df.columns else "—"
pain = max_pain(df)
net_gex = float(df["gex"].sum()) if "gex" in df.columns else None
pcr = put_call_ratio(df)
atm = atm_iv(df, spot)
walls = oi_walls(df)
flip = gamma_flip_strike(df) if "gex" in df.columns else None

m = st.columns(8)
m[0].metric("Spot", f"{spot:,.2f}")
m[1].metric("Expiry", str(expiry)[:11])
m[2].metric("Max pain", f"{pain:,.0f}" if pain else "—")
m[3].metric("Net GEX", f"{net_gex:,.0f}" if net_gex is not None else "—")
m[4].metric("PCR", f"{pcr:.2f}" if pcr is not None else "—")
m[5].metric("ATM IV", f"{atm:.1%}" if atm is not None else "—")
m[6].metric("Call wall", f"{walls['call_resistance']:,.0f}" if walls["call_resistance"] else "—")
m[7].metric("Put wall", f"{walls['put_support']:,.0f}" if walls["put_support"] else "—")
st.caption(
    f"Last update: {latest.strftime('%Y-%m-%d %H:%M:%S')}"
    + (f" · Gamma flip ≈ {flip:,.0f}" if flip else "")
)

df_near = df[(df["strike"] > spot - strike_window) & (df["strike"] < spot + strike_window)]

tab_oi, tab_gex, tab_hist, tab_data = st.tabs(["OI & IV", "GEX", "History", "Data"])

with tab_oi:
    c1, c2 = st.columns(2)
    with c1:
        fig_oi = px.bar(
            df_near,
            x="strike",
            y="oi",
            color="type",
            barmode="group",
            color_discrete_map={"CE": "#e74c3c", "PE": "#27ae60"},
            title=f"Open interest (±{strike_window})",
        )
        st.plotly_chart(fig_oi, use_container_width=True)
    with c2:
        fig_iv = px.line(
            df_near,
            x="strike",
            y="iv",
            color="type",
            markers=True,
            title="IV smile",
        )
        st.plotly_chart(fig_iv, use_container_width=True)

    if "change_in_oi" in df.columns:
        fig_coi = px.bar(
            df_near,
            x="strike",
            y="change_in_oi",
            color="type",
            barmode="group",
            color_discrete_map={"CE": "#e74c3c", "PE": "#27ae60"},
            title="Change in OI",
        )
        st.plotly_chart(fig_coi, use_container_width=True)

with tab_gex:
    if "gex" not in df.columns:
        from metrics import dealer_gex

        df["gex"] = dealer_gex(df["gamma"], df["oi"], df["type"])
    df_gex = df[
        (df["strike"] > spot - strike_window - 100)
        & (df["strike"] < spot + strike_window + 100)
    ]
    fig_gex = px.bar(
        df_gex,
        x="strike",
        y="gex",
        color="gex",
        color_continuous_scale=px.colors.diverging.RdYlGn,
        title="Net gamma exposure by strike",
    )
    if flip:
        fig_gex.add_vline(x=flip, line_dash="dash", annotation_text="γ flip")
    st.plotly_chart(fig_gex, use_container_width=True)

with tab_hist:
    try:
        hist = pd.read_sql(HISTORY_SQL, engine)
    except Exception:
        hist = pd.DataFrame()
    if not hist.empty and len(hist) > 1:
        hist = hist.sort_values("ingestion_timestamp")
        h1, h2 = st.columns(2)
        with h1:
            st.plotly_chart(
                px.line(hist, x="ingestion_timestamp", y="spot", markers=True, title="Spot"),
                use_container_width=True,
            )
        with h2:
            st.plotly_chart(
                px.line(hist, x="ingestion_timestamp", y="net_gex", markers=True, title="Net GEX"),
                use_container_width=True,
            )
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
            "gex",
        ]
        if c in df.columns
    ]
    view = df[show_cols].sort_values(["expiry", "strike"] if "expiry" in show_cols else ["strike"])
    st.dataframe(view, use_container_width=True, height=420)
    st.download_button(
        "Download latest snapshot CSV",
        data=view.to_csv(index=False),
        file_name=f"greeks_{latest.strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
