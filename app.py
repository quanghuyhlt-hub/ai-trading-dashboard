import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================= CONFIG =================
st.set_page_config(page_title="Full Market Scanner", layout="wide")
st.title("📡 FULL MARKET SCAN – HOSE + HNX")

# ================= LOAD STOCK LIST =================
@st.cache_data
def load_stock_list():
    return pd.read_csv("stocks.csv")["symbol"].dropna().tolist()

# ================= LOAD DATA =================
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

# ================= STRATEGY =================
def evaluate_stock(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Điều kiện lọc
    if last["Close"] <= last["MA50"]:
        return None

    if not (prev["MA20"] < prev["MA50"] and last["MA20"] > last["MA50"]):
        return None  # MA20 vừa cắt MA50

    risk = last["Close"] - last["MA50"]
    tp = last["Close"] + risk * 2
    rr = (tp - last["Close"]) / risk

    if rr < 1.8:
        return None

    # Phân tầng vốn
    if rr >= 2.5 and 55 <= last["RSI"] <= 70:
        tier = "ALL-IN KỸ THUẬT"
        capital = "80–100%"
    elif rr >= 2.0:
        tier = "CHỦ LỰC"
        capital = "50%"
    else:
        tier = "THĂM DÒ"
        capital = "20%"

    return {
        "Entry": round(last["Close"],2),
        "Stop Loss": round(last["MA50"],2),
        "RR": round(rr,2),
        "RSI": round(last["RSI"],1),
        "Phân bổ vốn": capital,
        "Khuyến nghị": tier
    }

# ================= UI =================
st.subheader("🚀 Quét toàn thị trường")

if st.button("📊 QUÉT TOÀN BỘ MÃ"):
    stock_list = load_stock_list()
    results = []

    with st.spinner(f"Đang quét {len(stock_list)} mã..."):
        for sym in stock_list:
            df = load_data(sym)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            res = evaluate_stock(df)

            if res:
                res["Mã"] = sym
                results.append(res)

    if results:
        df_result = pd.DataFrame(results)
        st.success(f"✅ Tìm được {len(df_result)} mã đạt chuẩn Trader")
        st.dataframe(df_result, use_container_width=True)
    else:
        st.warning("Không có mã nào đạt tiêu chí hiện tại.")
