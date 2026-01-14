import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================== CONFIG ==================
st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("📊 PRO TRADER – AUTO SCAN (MA20 CẮT MA50 SỚM)")

# ================== LOAD SYMBOL LIST ==================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df["symbol"].dropna().unique().tolist()

SYMBOLS = load_symbols()
st.caption(f"🔎 Đang quét {len(SYMBOLS)} cổ phiếu")

# ================== LOAD PRICE ==================
@st.cache_data
def load_price(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df

# ================== INDICATORS ==================
def add_indicators(df):
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    return df

# ================== MA20 CUT MA50 (SỚM) ==================
def ma_cross_early(df, lookback=5):
    df = df.dropna()
    if len(df) < lookback + 1:
        return False

    recent = df.tail(lookback + 1)
    for i in range(1, len(recent)):
        prev = recent.iloc[i - 1]
        curr = recent.iloc[i]
        if prev["MA20"] <= prev["MA50"] and curr["MA20"] > curr["MA50"]:
            return True
    return False

# ================== SCORING ==================
def calc_score(row):
    score = 0
    reasons = []

    if row["MA20"] > row["MA50"]:
        score += 25
        reasons.append("MA20 > MA50")

    if 45 <= row["RSI"] <= 65:
        score += 25
        reasons.append("RSI khỏe")

    dist = (row["Close"] - row["MA20"]) / row["MA20"] * 100
    if dist <= 5:
        score += 25
        reasons.append("Giá chưa chạy xa MA20")

    if row["Volume"] > row["VOL_MA20"]:
        score += 25
        reasons.append("Khối lượng ủng hộ")

    return score, round(dist, 2), " | ".join(reasons)

# ================== AUTO SCAN ==================
st.subheader("🧠 AUTO SCAN – SIÊU CỔ GIAI ĐOẠN ĐẦU")

results = []

progress = st.progress(0)
total = len(SYMBOLS)

for i, sym in enumerate(SYMBOLS):
    progress.progress((i + 1) / total)

    df = load_price(sym)
    if df.empty or len(df) < 60:
        continue

    df = add_indicators(df)

    if not ma_cross_early(df, lookback=5):
        continue

    last = df.iloc[-1]
    score, dist, reason = calc_score(last)

    if score >= 75:
        reco = "MUA"
    elif score >= 50:
        reco = "THEO DÕI"
    else:
        reco = "BỎ QUA"

    results.append({
        "Mã": sym,
        "Giá": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "Cách MA20 (%)": dist,
        "Score": score,
        "Khuyến nghị": reco,
        "Lý do": reason
    })

progress.empty()

# ================== DISPLAY ==================
if results:
    df_rs = pd.DataFrame(results).sort_values("Score", ascending=False)
    st.dataframe(df_rs, use_container_width=True)

    top = df_rs.iloc[0]
    st.markdown("### 🔥 MÃ NỔI BẬT NHẤT")
    st.success(
        f"""
        **{top['Mã']} – {top['Khuyến nghị']}**

        • Giá: {top['Giá']}  
        • RSI: {top['RSI']}  
        • Cách MA20: {top['Cách MA20 (%)']}%  

        👉 Lý do: {top['Lý do']}
        """
    )
else:
    st.warning("❌ Hiện không có mã nào đạt chuẩn MA20 cắt MA50 sớm.")
