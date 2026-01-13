import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================= CONFIG =================
st.set_page_config(page_title="Pro Trader – Early Entry", layout="wide")
st.title("📈 PRO TRADER – BẮT ĐIỂM VÀO SỚM")

# ================= STOCK LIST (DEMO) =================
VN_STOCKS = [
    "VNM.VN","HPG.VN","FPT.VN","MWG.VN","VIC.VN",
    "VCB.VN","CTG.VN","BID.VN","SSI.VN","VND.VN",
    "PNJ.VN","GMD.VN","POW.VN","STB.VN","TCB.VN"
]

# ================= DATA =================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="8mo", interval="1d", progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open","High","Low","Close","Volume"]]
    df.dropna(inplace=True)
    return df

# ================= INDICATORS =================
def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================= EARLY ENTRY CHECK =================
def early_entry_check(df):
    last = df.iloc[-1]

    # MA20 cắt MA50 trong 5 phiên gần nhất?
    recent = df.tail(6)
    cross = (
        recent["MA20"].iloc[-2] < recent["MA50"].iloc[-2] and
        recent["MA20"].iloc[-1] > recent["MA50"].iloc[-1]
    )

    # Giá cách MA20 bao nhiêu %
    dist_ma20 = (last["Close"] - last["MA20"]) / last["MA20"] * 100

    # Điều kiện
    conditions = {
        "cross": cross,
        "near_ma20": dist_ma20 <= 8,
        "trend_ok": last["Close"] > last["MA50"],
        "rsi_ok": 50 <= last["RSI"] <= 65
    }

    score = sum(conditions.values())

    if score == 4:
        rec = "🚀 MUA SỚM – ĐẦU SÓNG"
    elif score == 3:
        rec = "👀 THEO DÕI – CHỜ XÁC NHẬN"
    else:
        rec = "❌ LOẠI – CHƯA ĐẸP"

    return {
        "MA20 cắt MA50": "✔️" if cross else "❌",
        "Giá cách MA20 (%)": round(dist_ma20,2),
        "RSI": round(last["RSI"],2),
        "Khuyến nghị": rec
    }

# ================= UI =================
st.subheader("🔍 AUTO SCAN – BẮT ĐIỂM VÀO SỚM")

if st.button("🚀 QUÉT THỊ TRƯỜNG"):
    results = []

    with st.spinner("Đang quét..."):
        for sym in VN_STOCKS:
            df = load_data(sym)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            res = early_entry_check(df)

            results.append({
                "Mã": sym,
                **res
            })

    if results:
        df_result = pd.DataFrame(results)
        st.dataframe(df_result, use_container_width=True)
    else:
        st.warning("Không có mã phù hợp thời điểm hiện tại.")
