import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================= CONFIG =================
st.set_page_config(page_title="Pro Trader – Capital Allocation", layout="wide")
st.title("💰 PRO TRADER – PHÂN TẦNG VỐN & KHUYẾN NGHỊ")

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

# ================= CAPITAL LOGIC =================
def capital_allocation(entry, sl, rsi):
    risk = entry - sl
    tp = entry + risk * 2
    rr = (tp - entry) / risk

    if rr < 1.5:
        return None

    if rr >= 2.5 and 55 <= rsi <= 70:
        return "ALL-IN KỸ THUẬT", "80–100%", rr

    if rr >= 2.0:
        return "CHỦ LỰC", "50%", rr

    return "THĂM DÒ", "20%", rr

# ================= UI =================
st.subheader("📊 AUTO SCAN – PHÂN TẦNG VỐN")

if st.button("🚀 QUÉT & PHÂN BỔ VỐN"):
    rows = []

    with st.spinner("Đang scan và chia vốn..."):
        for sym in VN_STOCKS:
            df = load_data(sym)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            last = df.iloc[-1]

            if last["Close"] <= last["MA50"]:
                continue

            result = capital_allocation(
                last["Close"],
                last["MA50"],
                last["RSI"]
            )

            if result:
                tier, capital, rr = result
                rows.append({
                    "Mã": sym,
                    "Entry": round(last["Close"],2),
                    "Stop Loss": round(last["MA50"],2),
                    "RR": round(rr,2),
                    "RSI": round(last["RSI"],1),
                    "Phân bổ vốn": capital,
                    "Khuyến nghị": tier
                })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.warning("Không có kèo đạt chuẩn Trader.")
