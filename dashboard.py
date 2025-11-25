import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import time

# Page Configuration (Browser Tab Title)
st.set_page_config(page_title="Nifty Greeks Engine", layout="wide")

# Connect to DB (Use 127.0.0.1)
engine = create_engine('postgresql://admin:password@127.0.0.1:5432/options_db')

st.title("⚡ Nifty 50: Real-Time Gamma Exposure & Greeks")
st.markdown("Automated Pipeline: **NSE API** → **Python/Pandas** → **PostgreSQL** → **Streamlit**")

# Auto-Refresh Logic (Refresh every 10 seconds)
if st.button('Refresh Data'):
    st.rerun()

# 1. Fetch Latest Data
query = """
SELECT * FROM nifty_greeks_realtime 
WHERE ingestion_timestamp = (SELECT MAX(ingestion_timestamp) FROM nifty_greeks_realtime)
"""
try:
    df = pd.read_sql(query, engine)
except Exception as e:
    st.error("Waiting for ETL script to populate data...")
    st.stop()

if not df.empty:
    # Top Metrics
    latest_time = df['ingestion_timestamp'].iloc[0].strftime('%H:%M:%S')
    spot_price = df['underlying'].iloc[0]
    st.success(f"Last Updated: {latest_time} | NIFTY Spot: {spot_price}")

    # Layout: 2 Columns
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Open Interest (Support/Resistance)")
        # Filter for relevant strikes (Spot +/- 500)
        df_near = df[(df['strike'] > spot_price - 500) & (df['strike'] < spot_price + 500)]
        fig_oi = px.bar(df_near, x='strike', y='oi', color='type',
                        title="Open Interest Distribution", barmode='group',
                        color_discrete_map={'CE': 'red', 'PE': 'green'})
        st.plotly_chart(fig_oi, use_container_width=True)

    with col2:
        st.subheader("📉 Implied Volatility (The 'Smile')")
        fig_iv = px.line(df_near, x='strike', y='iv', color='type',
                         title="IV Structure (Volatility Smile)", markers=True)
        st.plotly_chart(fig_iv, use_container_width=True)

    # 3. The "Wilson Lin" Feature: Gamma Exposure
    st.subheader("☢️ Net Gamma Exposure (Market Maker Positioning)")

    # Simple GEX Proxy: Gamma * OI * 100 (for contract size)
    # Call GEX is positive, Put GEX is negative (dealers sell calls, buy puts usually)
    df['gex'] = df.apply(lambda x: (x['gamma'] * x['oi'] * 100) if x['type'] == 'CE'
    else (x['gamma'] * x['oi'] * -100), axis=1)

    df_gex = df[(df['strike'] > spot_price - 600) & (df['strike'] < spot_price + 600)]

    fig_gex = px.bar(df_gex, x='strike', y='gex',
                     title="Net Gamma Exposure (Positive = Dealer Long Gamma)",
                     color='gex', color_continuous_scale=px.colors.diverging.RdYlGn)
    st.plotly_chart(fig_gex, use_container_width=True)

    st.markdown("---")
    st.write("### Raw Data View")
    st.dataframe(df.head(10))

else:
    st.warning("Data table exists but is empty. Wait for the ETL script to finish the first batch.")