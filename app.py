import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Stock Trading Dashboard")

@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    df.dropna(inplace=True)
    return df

symbol = st.text_input(
    "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
    "VNM.VN"
)

df = load_data(symbol)

# 🚨 CHẶN LỖI TUYỆT ĐỐI
if df.empty or len(df) < 50:
    st.error("❌ Không lấy được dữ liệu hoặc dữ liệu không đủ.")
    st.stop()

# ===== INDICATORS (TỰ TÍNH – KHÔNG TA) =====

# MA
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()

# RSI
delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12, adjust=False).mean()
ema26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = ema12 - ema26
df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

df.dropna(inplace=True)

# ===== CHART =====
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

# ===== SIGNAL =====
latest = df.iloc[-1]

st.subheader("📌 Phân tích nhanh")

if latest["Close"] > latest["MA20"] > latest["MA50"] and latest["RSI"] < 70:
    st.success("✅ TÍN HIỆU: MUA – Xu hướng tăng khỏe")
elif latest["RSI"] > 70:
    st.warning("⚠️ QUÁ MUA – Dễ điều chỉnh")
else:
    st.info("⏳ CHƯA RÕ – Nên quan sát")

st.write(f"RSI: {latest['RSI']:.2f}")
st.write(f"MACD: {latest['MACD']:.2f}")
