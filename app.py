import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================== CONFIG ==================
st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("📊 PRO TRADER – AUTO STOCK SCAN (VN)")

# ================== LOAD SYMBOL LIST ==================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df["symbol"].dropna().unique().tolist()

# ================== LOAD PRICE DATA ==================
@st.cache_data
def load_price(symbol):
    df = yf.download(symbol + ".VN", period="6mo", interval="1d", progress=False)
    if df.empty or len(df) < 60:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)

    # Indicators
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================== MA CROSS CHECK ==================
def ma20_cross_recent(df, lookback=5):
    for i in range(1, lookback + 1):
        if (
            df["MA20"].iloc[-i] > df["MA50"].iloc[-i]
            and df["MA20"].iloc[-i - 1] <= df["MA50"].iloc[-i - 1]
        ):
            return True
    return False

# ================== SCORING ==================
def analyze_stock(df):
    last = df.iloc[-1]

    score = 0
    notes = []

    if last["Close"] > last["MA20"]:
        score += 1
        notes.append("Giá trên MA20")

    if last["MA20"] > last["MA50"]:
        score += 1
        notes.append("Xu hướng tăng (MA20 > MA50)")

    if ma20_cross_recent(df):
        score += 2
        notes.append("MA20 vừa cắt lên MA50")

    if 50 <= last["RSI"] <= 70:
        score += 1
        notes.append("RSI khỏe")

    if last["Volume"] > last["VOL_MA20"]:
        score += 1
        notes.append("Volume tăng")

    dist = (last["Close"] - last["MA20"]) / last["MA20"] * 100
    if dist < 8:
        score += 1
        notes.append("Chưa tăng quá nóng")

    return score, "; ".join(notes), dist

# ================== MAIN ==================
symbols = load_symbols()
results = []

st.info(f"🔍 Đang quét {len(symbols)} mã...")

for sym in symbols:
    df = load_price(sym)
    if df is None:
        continue

    score, note, dist = analyze_stock(df)
    last = df.iloc[-1]

    if score >= 5:
        reco = "MUA SỚM"
    elif score >= 4:
        reco = "THEO DÕI"
    else:
        reco = "BỎ QUA"

    results.append({
        "Mã": sym,
        "Giá": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "MA20 > MA50": "✔️" if last["MA20"] > last["MA50"] else "❌",
        "Volume tăng": "✔️" if last["Volume"] > last["VOL_MA20"] else "❌",
        "Khoảng cách MA20 (%)": round(dist, 1),
        "Điểm": score,
        "Khuyến nghị": reco,
        "Giải thích": note
    })

# ================== OUTPUT ==================
if results:
    df_out = pd.DataFrame(results)
    df_out = df_out.sort_values("Điểm", ascending=False)
    st.dataframe(df_out, use_container_width=True)
else:
    st.warning("Không có mã nào đạt tiêu chí.")
