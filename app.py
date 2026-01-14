import streamlit as st
import pandas as pd
import numpy as np
from vnstock import stock_historical_data

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Level X – Pro Trader Scanner",
    layout="wide"
)

st.title("🚀 Level X – Pro Trader Scanner")
st.caption("Dữ liệu Việt Nam | Scan vào sóng | Không dùng Yahoo")

# =========================
# LOAD SYMBOL LIST
# =========================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df["symbol"].dropna().unique().tolist()

symbols = load_symbols()

# =========================
# LOAD PRICE DATA
# =========================
def load_price(symbol):
    df = stock_historical_data(
        symbol=symbol,
        start_date="2023-01-01",
        end_date=pd.Timestamp.today().strftime("%Y-%m-%d"),
        resolution="1D"
    )
    df = df.rename(columns={
        "close": "Close",
        "volume": "Volume"
    })
    return df

# =========================
# INDICATORS
# =========================
def add_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# =========================
# ANALYSIS LOGIC
# =========================
def analyze_stock(symbol):
    try:
        df = load_price(symbol)
        if len(df) < 60:
            return None

        df = add_indicators(df)
        last = df.iloc[-1]

        score = 0
        notes = []

        if last["MA20"] > last["MA50"]:
            score += 30
            notes.append("MA20 > MA50 (xu hướng tăng)")
        else:
            notes.append("MA20 < MA50")

        if 50 <= last["RSI"] <= 70:
            score += 25
            notes.append("RSI khỏe")

        if last["Close"] > last["MA20"]:
            score += 25
            notes.append("Giá trên MA20")

        vol_ratio = df["Volume"].iloc[-1] / df["Volume"].rolling(20).mean().iloc[-1]
        if vol_ratio > 1.2:
            score += 20
            notes.append("Volume xác nhận")

        if score >= 80:
            verdict = "🔥 MUA THỬ – VÀO SÓNG"
        elif score >= 60:
            verdict = "👀 THEO DÕI"
        else:
            verdict = "❌ CHƯA ĐẸP"

        return {
            "Mã": symbol,
            "Giá": round(last["Close"], 2),
            "RSI": round(last["RSI"], 1),
            "MA20": round(last["MA20"], 2),
            "MA50": round(last["MA50"], 2),
            "Score": score,
            "Khuyến nghị": verdict,
            "Ghi chú": "; ".join(notes)
        }

    except Exception:
        return None

# =========================
# UI
# =========================
if st.button("🚀 AUTO SCAN PRO"):
    results = []
    with st.spinner("Đang quét dữ liệu Việt Nam…"):
        for s in symbols:
            r = analyze_stock(s)
            if r:
                results.append(r)

    if results:
        df = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.success(f"Quét xong {len(df)} mã")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Không có mã phù hợp")
