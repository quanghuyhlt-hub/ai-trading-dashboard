import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# =====================
# CONFIG
# =====================
st.set_page_config(
    page_title="AI Trading Dashboard",
    layout="wide"
)

st.title("📈 AI Trading Dashboard – Level X")
st.caption("Phân tích kỹ thuật cơ bản | Demo học thuật – không phải khuyến nghị đầu tư")

# =====================
# SIDEBAR
# =====================
st.sidebar.header("⚙️ Cấu hình")

symbol = st.sidebar.text_input("Mã cổ phiếu / Index", "VNINDEX")
period = st.sidebar.selectbox(
    "Khoảng thời gian",
    ["3mo", "6mo", "1y", "2y", "5y"],
    index=2
)

# =====================
# LOAD DATA
# =====================
@st.cache_data
def load_data(symbol, period):
    df = yf.download(symbol, period=period)
    df.dropna(inplace=True)
    return df

df = load_data(symbol, period)

if df.empty:
    st.error("❌ Không tải được dữ liệu. Kiểm tra lại mã.")
    st.stop()

# =====================
# INDICATORS
# =====================
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df["RSI"] = 100 - (100 / (1 + rs))

# =====================
# LAYOUT
# =====================
col1, col2 = st.columns([2, 1])

# =====================
# PRICE CHART
# =====================
with col1:
    st.subheader("📊 Biểu đồ giá")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df.index, df["Close"], label="Close")
    ax.plot(df.index, df["MA20"], label="MA20")
    ax.plot(df.index, df["MA50"], label="MA50")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

# =====================
# QUICK ANALYSIS (FIX LỖI 100%)
# =====================
with col2:
    st.subheader("⚡ Phân tích nhanh")

    latest_close = float(df["Close"].iloc[-1])
    ma20 = float(df["MA20"].iloc[-1])
    ma50 = float(df["MA50"].iloc[-1])
    rsi = float(df["RSI"].iloc[-1])

    st.metric("Giá hiện tại", f"{latest_close:,.2f}")

    # Trend
    if latest_close > ma20 > ma50:
        st.success("📈 Xu hướng: TĂNG")
    elif latest_close < ma20 < ma50:
        st.error("📉 Xu hướng: GIẢM")
    else:
        st.warning("⚠️ Xu hướng: SIDEWAYS")

    # RSI
    if rsi > 70:
        st.warning(f"RSI {rsi:.1f} – Quá mua")
    elif rsi < 30:
        st.success(f"RSI {rsi:.1f} – Quá bán")
    else:
        st.info(f"RSI {rsi:.1f} – Trung tính")

# =====================
# RAW DATA
# =====================
with st.expander("📄 Xem dữ liệu thô"):
    st.dataframe(df.tail(20))

# =====================
# FOOTER
# =====================
st.markdown("---")
st.caption("Built with Streamlit | Demo AI Trading Dashboard")
