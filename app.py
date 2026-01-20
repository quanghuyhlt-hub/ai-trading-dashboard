import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("📈 PRO TRADER STOCK SCANNER")

# ======================
# LOAD SYMBOL LIST
# ======================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df["symbol"].dropna().unique().tolist()

# ======================
# INDICATORS
# ======================
def compute_indicators(df):
    df = df.copy()

    # ===== Moving Averages =====
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    # ===== RSI =====
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # ===== ADX (FIX CHUẨN) =====
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    plus_dm = high.diff()
    minus_dm = low.diff() * -1

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr14 = tr.rolling(14).sum()
    plus_di = 100 * plus_dm.rolling(14).sum() / tr14
    minus_di = 100 * minus_dm.rolling(14).sum() / tr14

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    df["ADX"] = dx.rolling(14).mean()

    # ===== Volume =====
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    return df
# ======================
# SCAN LOGIC
# ======================
def scan_symbol(symbol):
    df = yf.download(symbol, period="1y", interval="1d", progress=False)
    if df.empty or len(df) < 220:
        return None

    df = compute_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    cross_up = prev["MA20"] <= prev["MA50"] and last["MA20"] > last["MA50"]
    price_above_ma200 = last["Close"] > last["MA200"]
    rsi_ok = last["RSI"] > 50
    volume_ok = last["Volume"] > 1.5 * last["VOL_MA20"]
    trend_ok = last["ADX"] > 20

    if not all([cross_up, price_above_ma200, rsi_ok, volume_ok, trend_ok]):
        return None

    score = 0
    score += 20 if last["MA20"] > last["MA50"] > last["MA200"] else 0
    score += 20 if last["ADX"] > 25 else 10
    score += 15 if last["RSI"] > 60 else 10
    score += 25 if volume_ok else 0
    score += 20 if last["Close"] >= df["High"].rolling(20).max().iloc[-1] else 10

    recommendation = "MUA THEO BREAKOUT" if score >= 80 else "THEO DÕI CHỜ PULLBACK"

    return {
        "Mã": symbol,
        "Giá": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "ADX": round(last["ADX"], 1),
        "Vol/MA20": round(last["Volume"] / last["VOL_MA20"], 2),
        "Score": score,
        "Khuyến nghị": recommendation
    }

# ======================
# UI
# ======================
if st.button("🚀 SCAN TOÀN BỘ DANH SÁCH"):
    symbols = load_symbols()
    results = []

    progress = st.progress(0)
    for i, sym in enumerate(symbols):
        res = scan_symbol(sym)
        if res:
            results.append(res)
        progress.progress((i + 1) / len(symbols))

    if results:
        df_out = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.subheader("📊 KẾT QUẢ SCAN")
        st.dataframe(df_out, use_container_width=True)
    else:
        st.warning("Không có mã nào đạt đủ điều kiện.")
