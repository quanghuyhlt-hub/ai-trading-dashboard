import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Stock Auto Scan", layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d")
    if df.empty:
        return None

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    return df.dropna()


# =========================
# ADD INDICATORS
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

    # Đếm số phiên từ lúc cắt (ngược thời gian)
    df["DAYS_FROM_CROSS"] = (
        df["MA_CROSS_UP"]
        .iloc[::-1]
        .cumsum()
        .iloc[::-1]
    )

    df["DIST_TO_MA20"] = (df["close"] - df["MA20"]) / df["MA20"] * 100

    return df.dropna()


# =========================
# UI
# =========================
st.title("📈 Ứng dụng lọc cổ phiếu – MA20 cắt MA50")

tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])


# =========================
# TAB 1: PHÂN TÍCH 1 MÃ
# =========================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)", "VNM.VN")

    if symbol:
        df = load_data(symbol)
        if df is None:
            st.error("❌ Không tải được dữ liệu")
        else:
            df = add_indicators(df)
            last = df.iloc[-1]

            st.subheader(f"📊 {symbol}")
            st.metric("Giá đóng cửa", round(last["close"], 2))
            st.metric("MA20", round(last["MA20"], 2))
            st.metric("MA50", round(last["MA50"], 2))

            if (
                last["MA20"] > last["MA50"]
                and last["DAYS_FROM_CROSS"] <= 5
                and last["DIST_TO_MA20"] <= 8
            ):
                st.success(
                    """
                    ✅ **TÍN HIỆU TÍCH CỰC**
                    - MA20 vừa cắt lên MA50 (≤ 5 phiên)
                    - Giá chưa tăng quá xa MA20

                    👉 **Chiến lược tham khảo**
                    - Canh mua khi điều chỉnh nhẹ
                    - Stoploss dưới MA50
                    """
                )
            else:
                st.warning("⚠️ Chưa phải thời điểm vào lệnh an toàn")


# =========================
# TAB 2: AUTO SCAN
# =========================
with tab2:
    st.subheader("🧠 AUTO SCAN – MA20 cắt MA50 GẦN ĐÂY")

    symbols_text = st.text_area(
        "Danh sách mã (mỗi mã 1 dòng)",
        "VNM.VN\nHPG.VN\nFPT.VN\nMWG.VN\nSSI.VN"
    )

    symbols = [s.strip() for s in symbols_text.split("\n") if s.strip()]

    if st.button("🚀 Bắt đầu quét"):
        results = []

        for symbol in symbols:
            df = load_data(symbol)
            if df is None or len(df) < 60:
                continue

            df = add_indicators(df)
            last = df.iloc[-1]

            scan_ok = (
                last["MA20"] > last["MA50"]
                and last["DAYS_FROM_CROSS"] <= 5
                and last["DIST_TO_MA20"] <= 8
                and last["volume"] > last["VOL_MA20"]
            )

            if scan_ok:
                results.append({
                    "Mã": symbol,
                    "Giá": round(last["close"], 2),
                    "MA20": round(last["MA20"], 2),
                    "MA50": round(last["MA50"], 2),
                    "Số phiên từ lúc cắt": int(last["DAYS_FROM_CROSS"]),
                    "Khoảng cách tới MA20 (%)": round(last["DIST_TO_MA20"], 2),
                    "Khuyến nghị": "THEO DÕI / CANH MUA"
                })

        if results:
            st.success(f"✅ Tìm thấy {len(results)} cổ phiếu đạt điều kiện")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("❌ Không có cổ phiếu nào đủ chuẩn hôm nay")
