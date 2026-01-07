import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")

st.title("📊 Level X – Stock Trading Dashboard")

@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d")
    df.dropna(inplace=True)
    return df

symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN)", "VNM.VN")

df = load_data(symbol)

# Indicators
df["RSI"] = RSIIndicator(df["Close"]).rsi()
macd = MACD(df["Close"])
df["MACD"] = macd.macd()
df["MACD_SIGNAL"] = macd.macd_signal()
df["MA20"] = SMAIndicator(df["Close"], window=20).sma_indicator()
df["MA50"] = SMAIndicator(df["Close"], window=50).sma_indicator()

# Chart
fig = go.Figure()
fig.add_candlestick(
    x=df.index,
    open=df["Open"],
    high=df["High"],
    low=df["Low"],
    close=df["Close"],
    name="Price"
)
fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))

fig.update_layout(height=600)
st.plotly_chart(fig, use_container_width=True)

# Signal logic
latest = df.iloc[-1]

st.subheader("📌 Phân tích nhanh")

if latest["Close"] > latest["MA20"] > latest["MA50"] and latest["RSI"] < 70:
    st.success("✅ TÍN HIỆU: MUA – Xu hướng tăng, động lượng tốt")
elif latest["RSI"] > 70:
    st.warning("⚠️ QUÁ MUA – Cẩn trọng điều chỉnh")
else:
    st.info("⏳ CHƯA RÕ XU HƯỚNG – Theo dõi thêm")

st.write(f"RSI: {latest['RSI']:.2f}")
st.write(f"MACD: {latest['MACD']:.2f}")
