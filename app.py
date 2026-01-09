import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(
    page_title="Auto Scan MA20/MA50",
    layout="wide"
)

# =========================
# LOAD DATA (FIX MULTIINDEX)
# =========================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return None

    # FIX lỗi MultiIndex của yfinance
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

    # MA20 cắt lên MA50
    df["MA_CROSS_UP"] = (
        (df["MA20"] > df["MA50"]) &
        (df["MA20"].shift(1) <= df["MA50"].shift(1))
    )

    # Số phiên kể từ lần cắt gần nhất
    df["DAYS_FROM_CROSS"] = np.nan
    cross_idx = df.index[df["MA_CROSS_UP"]]

    if len(cross_idx) > 0:
        last_cross = cross_idx[-1]
        df.loc[last_cross:, "DAYS_FROM_CROSS"] = range(len(df.loc[last_cross:]))

    # Giá đã đi xa MA20 bao nhiêu %
    df["DIST_TO_MA20"] = ((df["close"] - df["MA20"]) / df["MA20"]) * 100

    return df.dropna()


# =========================
# UI
# =========================
st.title("📈 AUTO SCAN – MA20 cắt MA50 (Điểm vào sớm)")

tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])


# =========================
# TAB 1 – PHÂN TÍCH 1 MÃ
# =========================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN)", "VNM.VN")

    if symbol:
        df = load_data(symbol)

        if df is None:
            st.error("❌ Không tải được dữ liệu")
        else:
            df = add_indicators(df)
            last = df.iloc[-1]

            st.subheader(f"📌 {symbol}")

            col1, col2, col3 = st.columns(3)

            col1.metric("Giá hiện tại", round(last["close"], 2))
            col2.metric("MA20", round(last["MA20"], 2))
            col3.metric("MA50", round(last["MA50"], 2))

            if last["MA20"] > last["MA50"]:
                st.success("✅ Xu hướng tăng (MA20 > MA50)")
            else:
                st.warning("⚠️ Xu hướng chưa rõ ràng")

            if last["DIST_TO_MA20"] < 5:
                st.info("🎯 Giá còn gần MA20 – chưa bị kéo quá xa")
            else:
                st.warning("🚨 Giá đã tăng khá xa MA20 – cân nhắc rủi ro")

            st.dataframe(df.tail(20))


# =========================
# TAB 2 – AUTO SCAN
# =========================
with tab2:
    st.subheader("🧠 Lọc cổ phiếu MA20 vừa cắt MA50")

    symbols = st.text_area(
        "Danh sách mã (mỗi mã 1 dòng)",
        "VNM.VN\nHPG.VN\nFPT.VN\nMWG.VN"
    )

    max_days = st.slider(
        "Số phiên tối đa kể từ lúc MA20 cắt MA50",
        min_value=1,
        max_value=20,
        value=5
    )

    if st.button("🚀 SCAN"):
        results = []

        for sym in symbols.splitlines():
            sym = sym.strip()
            if not sym:
                continue

            df = load_data(sym)
            if df is None:
                continue

            df = add_indicators(df)
            last = df.iloc[-1]

            if (
                last["MA20"] > last["MA50"]
                and last["DAYS_FROM_CROSS"] <= max_days
                and last["DIST_TO_MA20"] < 7
            ):
                results.append({
                    "Mã": sym,
                    "Giá": round(last["close"], 2),
                    "Phiên từ MA20 cắt MA50": int(last["DAYS_FROM_CROSS"]),
                    "Cách MA20 (%)": round(last["DIST_TO_MA20"], 2),
                    "Nhận định": "Điểm vào sớm – chưa bị kéo quá xa"
                })

        if results:
            st.success(f"✅ Tìm được {len(results)} mã phù hợp")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("❌ Không có mã nào đạt điều kiện")
