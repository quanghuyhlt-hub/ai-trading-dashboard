import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import ta

st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

st.title("📈 AI Trading Dashboard – Level X")

# ======================
# Sidebar
# ======================
symbol = st.sidebar.text_input("Nhập mã cổ phiếu (HOSE / HNX)", "VNM")
period = st.sidebar.selectbox("Khung thời gian", ["6mo", "1y", "2y", "5y"])
interval = st.sidebar.selectbox("Độ phân giải", ["1d", "1wk"])

# ======================
# Load data
# ======================
@st.cache_data
def load_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval)
    df.dropna(inplace=True)
    return df

df = load_data(symbol, period, interval)

if df.empty:
    st.error("❌ Không tải được dữ liệu")
    st.stop()

# ======================
# Indicators
# ======================
df["MA20"] = ta.trend.sma_indicator(df["Close"], window=20)
df["MA50"] = ta.trend.sma_indicator(df["Close"], window=50)
df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

# ======================
# Chart
# ======================
st.subheader("📊 Biểu đồ giá")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df.index, df["Close"], label="Close", linewidth=2)
ax.plot(df.index, df["MA20"], label="MA20")
ax.plot(df.index, df["MA50"], label="MA50")
ax.legend()
ax.grid(True)

st.pyplot(fig)

# ======================
# PHÂN TÍCH NHANH (ĐÃ FIX LỖI)
# ======================
latest_close = float(df["Close"].iloc[-1])
ma20 = float(df["MA20"].iloc[-1])
ma50 = float(df["MA50"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])

st.subheader("⚡ Phân tích nhanh")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Giá hiện tại", f"{latest_close:,.2f}")
col2.metric("MA20", f"{ma20:,.2f}")
col3.metric("MA50", f"{ma50:,.2f}")
col4.metric("RSI", f"{rsi:.1f}")

# Xu hướng
if latest_close > ma20 and ma20 > ma50:
    st.success("📈 Xu hướng: TĂNG – Ưu tiên MUA")
elif latest_close < ma20 and ma20 < ma50:
    st.error("📉 Xu hướng: GIẢM – Không nên vào lệnh")
else:
    st.warning("⚠️ Xu hướng: SIDEWAYS – Quan sát")

# RSI cảnh báo
if rsi > 70:
    st.warning("⚠️ RSI cao – Có thể quá mua")
elif rsi < 30:
    st.success("✅ RSI thấp – Có thể quá bán")
else:
    st.info("ℹ️ RSI trung tính")

# ======================
# GỢI Ý GIAO DỊCH (CƠ BẢN)
# ======================
st.subheader("🎯 Gợi ý giao dịch (tham khảo)")

swing_low = df["Low"].tail(30).min()
swing_high = df["High"].tail(30).max()

tp1 = latest_close + (swing_high - swing_low) * 0.382
tp2 = latest_close + (swing_high - swing_low) * 0.618
sl = swing_low

st.write(f"🟢 **Điểm vào tham khảo**: {latest_close:,.2f}")
st.write(f"🎯 **Chốt lời 1 (TP1 – Fib 0.382)**: {tp1:,.2f}")
st.write(f"🎯 **Chốt lời 2 (TP2 – Fib 0.618)**: {tp2:,.2f}")
st.write(f"🔴 **Cắt lỗ (SL)**: {sl:,.2f}")

st.caption("⚠️ Chỉ mang tính hỗ trợ quyết định, không phải khuyến nghị đầu tư.")
