import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Auto Scan MA20/MA50", layout="wide")


# =========================
# LOAD DATA (FIX MULTIINDEX)
# =========================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)

    if df.empty:
        return None

    # Nếu là MultiIndex (lỗi chính của sếp)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    return df.dropna()


# =========================
# INDICATORS
# =========================
def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["VOL_MA20"] = df["volume"].rolling(20).mean()

    df["MA_CROSS_UP"] = (
        (df["MA20"] > df["MA50"]) &
        (df["MA20"].shift(1) <= df["MA50"].shift(1))
    )

    # số phiên kể từ lần cắt gần nhất
    cross_idx = df.index[df["MA_CROSS_UP"]]
    df["DAYS_FROM_CROSS"] = np.nan

    if len(cross_idx) > 0:
        last_cross = cross_idx[-1]
        df.loc[last_cross:, "DAYS_FROM_CROSS"] = range(len(df.loc[last_cross:]))

    df["DIST_TO_MA20"] = ((df["close"] - df["MA20"]) / df["MA20"]) * 100

    return df.dropna()


# =========================
# UI
# =========================
st.title("📈 AUTO SCAN – MA20 cắt MA50 (Điểm vào sớm)")

tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])


# =========================
# TAB 1
# =========================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu", "VNM.VN")

    if symbol:
        df = load_data(symbol)

        if df is
