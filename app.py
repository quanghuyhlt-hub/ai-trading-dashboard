import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ================= CONFIG =================
st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Stock Trading Dashboard")

# ================= STOCK LIST (DEMO) =================
VN_STOCKS = {
    "HOSE": ["VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN"],
    "HNX": ["SHS.VN", "PVS.VN", "IDC.VN"]
}

ALL_SYMBOLS = VN_STOCKS["HOSE"] + VN_STOCKS["HNX"]

# ================= DATA LOADER =================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)

    return df

# ================= INDICATORS =================
def add_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================= TABS =================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🤖 AUTO SCAN (Level X++)"])

# =====================================================
# TAB 1 – PHÂN TÍCH 1 MÃ
# =====================================================
with tab1:
    symbol = st.text_input(
        "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
        "VNM.VN"
    )

    df = load_data(symbol)

    if df.empty or len(df) < 50:
        st.error("❌ Không lấy được dữ liệu hoặc dữ liệu không đủ.")
        st.stop()

    df = add_indicators(df)

    # ===== CHART =====
    fig = go.Figure()
    fig.add_candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    )
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))

    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)

    # ===== QUICK ANALYSIS =====
    st.subheader("📌 Phân tích nhanh")

    last_close = float(df["Close"].iloc[-1])
    ma20 = float(df["MA20"].iloc[-1])
    ma50 = float(df["MA50"].iloc[-1])
    rsi = float(df["RSI"].iloc[-1])

    if last_close > ma20 > ma50 and rsi < 70:
        st.success("✅ TÍN HIỆU: MUA – Xu hướng tăng khỏe")
    elif rsi >= 70:
        st.warning("⚠️ QUÁ MUA – Dễ điều chỉnh")
    else:
        st.info("⏳ CHƯA RÕ – Nên quan sát")

    st.write(f"RSI: {round(rsi, 2)}")

# =====================================================
# TAB 2 – AUTO SCAN (LEVEL X++)
# =====================================================
with tab2:
    st.subheader("🤖 AUTO SCAN – Tìm cổ phiếu tiềm năng")

    results = []

    with st.spinner("⏳ Đang quét thị trường..."):
        for sym in ALL_SYMBOLS:
            df = load_data(sym)
            if df.empty or len(df) < 50:
                continue

            df = add_indicators(df)

            last = df.iloc[-1]

            trend = "TĂNG" if last["Close"] > last["MA20"] > last["MA50"] else "KHÔNG RÕ"
            recommendation = "MUA" if trend == "TĂNG" and last["RSI"] < 70 else "THEO DÕI"

            results.append({
                "Mã": sym,
                "Giá hiện tại": round(last["Close"], 2),
                "RSI": round(last["RSI"], 2),
                "Xu hướng": trend,
                "Khuyến nghị": recommendation
            })

    if results:
        df_result = pd.DataFrame(results)
        st.dataframe(df_result, use_container_width=True)
    else:
        st.warning("⚠️ Không tìm được mã phù hợp.")
