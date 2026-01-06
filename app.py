import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="AI Trading Dashboard – Level X", layout="wide")

st.title("📊 AI TRADING DASHBOARD – LEVEL X")
st.caption("Demo version | Signals – Charts – Market Overview")

# ===== Fake market data (demo) =====
np.random.seed(42)
dates = pd.date_range(end=pd.Timestamp.today(), periods=100)

price = np.cumsum(np.random.randn(100)) + 100
df = pd.DataFrame({
    "Date": dates,
    "Price": price
})
df["MA20"] = df["Price"].rolling(20).mean()
df["MA50"] = df["Price"].rolling(50).mean()

# ===== Signal logic =====
df["Signal"] = np.where(df["MA20"] > df["MA50"], "BUY", "SELL")

# ===== Layout =====
col1, col2 = st.columns([3, 1])

with col1:
    fig = px.line(
        df,
        x="Date",
        y=["Price", "MA20", "MA50"],
        title="Price Chart + Moving Averages"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📌 Latest Signal")
    st.metric(
        label="Signal",
        value=df["Signal"].iloc[-1]
    )

    st.subheader("📈 Stats")
    st.write("Last Price:", round(df["Price"].iloc[-1], 2))
    st.write("MA20:", round(df["MA20"].iloc[-1], 2))
    st.write("MA50:", round(df["MA50"].iloc[-1], 2))

st.divider()
st.info("👉 Đây là bản demo Level X. Bước sau sẽ mở rộng: đa mã, đa sàn, backtest, AI assistant.")
