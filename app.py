import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Stock Scanner", layout="wide")
st.title("📊 Auto Scan cổ phiếu – Bảng hỗ trợ quyết định")

# ======================
# CONFIG
# ======================
DEFAULT_SYMBOLS = "VCB,CTG,BID,HPG,FPT,MWG,SSI"

# ======================
# INDICATORS (KHÔNG DÙNG TA)
# ======================
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def MACD(series, fast=12, slow=26):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow

def add_indicators(df):
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = RSI(df["Close"])
    df["MACD"] = MACD(df["Close"])
    return df

# ======================
# SCAN 1 MÃ
# ======================
def scan_symbol(symbol, period):
    try:
        df = yf.download(symbol, period=period, progress=False)
        if df.empty or len(df) < 60:
            return None

        df = add_indicators(df)
        last = df.iloc[-1]

        result = {
            "Mã": symbol,
            "MA20 > MA50": last["MA20"] > last["MA50"],
            "Giá > MA20": last["Close"] > last["MA20"],
            "RSI > 50": last["RSI"] > 50,
            "MACD > 0": last["MACD"] > 0,
        }

        result["Điểm"] = (
            result["MA20 > MA50"]
            + result["Giá > MA20"]
            + result["RSI > 50"]
            + result["MACD > 0"]
        )

        return result

    except Exception as e:
        return None

# ======================
# SIDEBAR
# ======================
symbols_input = st.sidebar.text_area(
    "Danh sách mã (phân cách bằng dấu ,)",
    DEFAULT_SYMBOLS
)
period = st.sidebar.selectbox("Khung dữ liệu", ["6mo", "1y", "2y"])
scan_btn = st.sidebar.button("🚀 Scan thị trường")

# ======================
# MAIN
# ======================
if scan_btn:
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    results = []

    with st.spinner("Đang quét thị trường..."):
        for sym in symbols:
            r = scan_symbol(sym, period)
            if r:
                results.append(r)

    if not results:
        st.error("❌ Không có mã hợp lệ")
        st.stop()

    df = pd.DataFrame(results)
    df = df.sort_values("Điểm", ascending=False)

    for col in ["MA20 > MA50", "Giá > MA20", "RSI > 50", "MACD > 0"]:
        df[col] = df[col].apply(lambda x: "✅" if x else "❌")

    st.subheader("📈 BẢNG SCAN QUYẾT ĐỊNH")
    st.dataframe(df, use_container_width=True)

    st.subheader("🧠 Nhận định nhanh")
    best = df.iloc[0]

    if best["Điểm"] >= 3:
        st.success(
            f"✅ **{best['Mã']}** là mã mạnh nhất hiện tại – có thể ưu tiên theo dõi"
        )
    else:
        st.warning("⚠️ Chưa có mã nào thật sự vượt trội – nên kiên nhẫn")
