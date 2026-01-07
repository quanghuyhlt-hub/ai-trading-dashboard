import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Level X++ Auto Scan", layout="wide")
st.title("🚀 Level X++ – AUTO SCAN CỔ PHIẾU")

# =====================
# DANH SÁCH MÃ (DEMO)
# =====================
VN_STOCKS = [
    "VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN",
    "SSI.VN", "VCB.VN", "CTG.VN", "ACB.VN", "BID.VN"
]

# =====================
# LOAD DATA
# =====================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df


# =====================
# CALCULATE INDICATORS
# =====================
def calculate_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    return df


# =====================
# SCORING SYSTEM
# =====================
def score_stock(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    if latest["Close"] > latest["MA20"] > latest["MA50"]:
        score += 3

    if 40 <= latest["RSI"] <= 65:
        score += 2
    elif latest["RSI"] < 30:
        score += 1

    if prev["Close"] < prev["MA20"] and latest["Close"] > latest["MA20"]:
        score += 1

    if latest["Volume"] > latest["VOL_MA20"]:
        score += 2

    return score


def rating(score):
    if score >= 7:
        return "🔥 STRONG BUY"
    elif score >= 5:
        return "✅ BUY"
    elif score >= 3:
        return "👀 WATCH"
    else:
        return "❌ SKIP"


# =====================
# AUTO SCAN
# =====================
st.subheader("📡 AUTO SCAN – LEVEL X++")

results = []

with st.spinner("Đang quét thị trường..."):
    for symbol in VN_STOCKS:
        df = load_data(symbol)

        if df.empty or len(df) < 50:
            continue

        df = calculate_indicators(df)
        score = score_stock(df)

        results.append({
            "Mã": symbol,
            "Giá hiện tại": round(df["Close"].iloc[-1], 2),
            "RSI": round(df["RSI"].iloc[-1], 2),
            "Xu hướng": "Tăng" if df["Close"].iloc[-1] > df["MA20"].iloc[-1] else "Giảm",
            "Điểm": score,
            "Khuyến nghị": rating(score)
        })

# =====================
# RESULT TABLE
# =====================
if results:
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("Điểm", ascending=False)

    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Không quét được mã nào.")
