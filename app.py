import streamlit as st
import pandas as pd
import yfinance as yf

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="Level X – Trading Dashboard",
    layout="wide"
)

st.title("📊 Level X – Trading Dashboard")

# ======================
# DATA FETCH
# ======================
def fetch_price(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y", interval="1d")
    if df.empty:
        return df
    df = df.reset_index()
    return df


@st.cache_data
def load_data(symbol):
    df = fetch_price(symbol)
    if df.empty:
        return df

    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    return df


# ======================
# MA20 CẮT MA50 GẦN ĐÂY
# ======================
def ma20_cross_ma50_recent(df, lookback=5):
    """
    True nếu MA20 vừa cắt lên MA50 trong lookback phiên gần nhất
    """
    if len(df) < 60:
        return False

    df = df.dropna().copy()
    df["prev_MA20"] = df["MA20"].shift(1)
    df["prev_MA50"] = df["MA50"].shift(1)

    recent = df.tail(lookback)

    cross = (
        (recent["prev_MA20"] < recent["prev_MA50"]) &
        (recent["MA20"] > recent["MA50"])
    )

    return cross.any()


# ======================
# TABS
# ======================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# ======================
# TAB 1 – SINGLE STOCK
# ======================
with tab1:
    symbol = st.text_input(
        "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
        value="VNM.VN"
    )

    if symbol:
        df = load_data(symbol)

        if df.empty:
            st.error("❌ Không lấy được dữ liệu")
        else:
            last = df.iloc[-1]

            st.subheader(f"📌 {symbol}")
            col1, col2, col3 = st.columns(3)

            col1.metric("Giá hiện tại", round(last["Close"], 2))
            col2.metric("MA20", round(last["MA20"], 2))
            col3.metric("MA50", round(last["MA50"], 2))

            if ma20_cross_ma50_recent(df):
                st.success("🔥 MA20 vừa cắt lên MA50 (tín hiệu sớm)")
            else:
                st.warning("⏳ Chưa có tín hiệu MA20 cắt MA50 gần đây")

            st.dataframe(df.tail(10))


# ======================
# TAB 2 – AUTO SCAN
# ======================
with tab2:
    st.subheader("🧠 Auto Scan – MA20 cắt MA50 GẦN ĐÂY")

    symbols = st.text_area(
        "Danh sách mã (mỗi mã 1 dòng)",
        value="VNM.VN\nHPG.VN\nFPT.VN\nVCB.VN\nMWG.VN"
    )

    lookback = st.slider(
        "Số phiên được coi là 'vừa cắt'",
        min_value=1,
        max_value=10,
        value=5
    )

    if st.button("🚀 SCAN"):
        results = []

        for sym in symbols.splitlines():
            sym = sym.strip()
            if not sym:
                continue

            df = load_data(sym)
            if df.empty:
                continue

            if ma20_cross_ma50_recent(df, lookback):
                last = df.iloc[-1]
                results.append({
                    "Mã": sym,
                    "Giá": round(last["Close"], 2),
                    "MA20": round(last["MA20"], 2),
                    "MA50": round(last["MA50"], 2)
                })

        if results:
            st.success(f"✅ Tìm thấy {len(results)} mã phù hợp")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("❌ Không có mã nào thỏa điều kiện")
