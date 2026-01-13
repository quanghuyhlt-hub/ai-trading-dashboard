import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Level X – Pro Trader Scanner", layout="wide")

# ================= RSI =================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================= LOAD DATA =================
@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    if df.empty:
        return None

    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    df["RSI"] = calc_rsi(df["Close"])
    df = df.dropna()

    if len(df) < 50:
        return None

    return df

# ================= ANALYZE =================
def analyze_stock(df):
    last = df.iloc[-1]

    close = float(last["Close"])
    ma20 = float(last["MA20"])
    ma50 = float(last["MA50"])
    vol = float(last["Volume"])
    vol_ma = float(last["VOL_MA20"])
    rsi = float(last["RSI"])

    score = 0
    notes = []

    if ma20 > ma50:
        score += 25
        notes.append("MA20 > MA50")

    if close > ma20:
        score += 15
        notes.append("Giá trên MA20")

    if 50 <= rsi <= 70:
        score += 15
        notes.append("RSI khỏe")

    if vol > vol_ma:
        score += 15
        notes.append("Volume xác nhận")

    dist = abs(close - ma20) / ma20 * 100
    if dist <= 3:
        score += 20
        notes.append("Giá sát MA20")

    # ===== Trading Plan =====
    entry = close
    stoploss = ma20 * 0.97
    risk = entry - stoploss
    target = entry + 2 * risk
    rr = round((target - entry) / risk, 2) if risk > 0 else 0

    if score >= 80 and rr >= 2:
        rating = "🔥 MUA THỬ NGHIỆM"
    elif score >= 70:
        rating = "👀 CHỜ PULLBACK"
    else:
        rating = "❌ KHÔNG GIAO DỊCH"

    return {
        "Giá": round(close, 2),
        "Score": score,
        "Entry": round(entry, 2),
        "Stoploss": round(stoploss, 2),
        "Target": round(target, 2),
        "R:R": rr,
        "Khuyến nghị": rating,
        "Lý do": "; ".join(notes)
    }

# ================= UI =================
st.title("🚀 Level X – Pro Trader Scanner")

symbols = [
    "VNM.VN","FPT.VN","MWG.VN","HPG.VN","SSI.VN",
    "PNJ.VN","GMD.VN","VND.VN","POW.VN","VIC.VN"
]

if st.button("🚀 AUTO SCAN PRO"):
    results = []

    with st.spinner("Đang scan như trader chuyên nghiệp..."):
        for sym in symbols:
            df = load_data(sym)
            if df is None:
                continue

            try:
                data = analyze_stock(df)
                data["Mã"] = sym
                results.append(data)
            except:
                continue

    if results:
        df_rs = pd.DataFrame(results).sort_values("Score", ascending=False)
        st.dataframe(df_rs, use_container_width=True)
    else:
        st.warning("Không có mã nào đạt điều kiện.")
