import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ================== CONFIG ==================
st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Trading Dashboard")

# ================== STOCK LIST (DEMO) ==================
VN_STOCKS = {
    "HOSE": ["VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN"],
    "HNX": ["SHS.VN", "PVS.VN", "IDC.VN"]
}

ALL_SYMBOLS = VN_STOCKS["HOSE"] + VN_STOCKS["HNX"]

# ================== DATA LOADER ==================
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

# ================== INDICATORS ==================
def add_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================== SCORING SYSTEM ==================
def score_stock(df):
    score = 0
    last = df.iloc[-1]

    if last["Close"] > last["MA20"] > last["MA50"]:
        score += 3
    if 40 <= last["RSI"] <= 65:
        score += 2
    if last["RSI"] < 30:
        score += 1
    if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1]:
        score += 2

    return score

def rating(score):
    if score >= 7:
        return "🔥 STRONG BUY"
    elif score >= 5:
        return "✅ BUY"
    elif score >= 3:
        return "👀 WATCH"
    else:
        return "❌ SKIP"

# ================== SESSION ==================
if "selected_symbol" not in st.session_state:
    st.session_state["selected_symbol"] = "VNM.VN"

# ================== TABS ==================
tab1, tab2 = st.tabs(["🔍 Soi chi tiết 1 mã", "📡 Auto Scan thị trường"])

# ================== TAB 2: AUTO SCAN ==================
with tab2:
    st.subheader("📡 Auto Scan – Lọc cổ phiếu tiềm năng")

    results = []

    for symbol in ALL_SYMBOLS:
        df = load_data(symbol)
        if df.empty or len(df) < 50:
            continue

        df = add_indicators(df)
        sc = score_stock(df)

        results.append({
            "Mã": symbol,
            "Giá": round(df["Close"].iloc[-1], 2),
            "RSI": round(df["RSI"].iloc[-1], 2),
            "Điểm": sc,
            "Khuyến nghị": rating(sc)
        })

    result_df = pd.DataFrame(results).sort_values("Điểm", ascending=False)

    st.dataframe(result_df, use_container_width=True)

    chosen = st.selectbox(
        "👉 Chọn mã để soi chi tiết:",
        result_df["Mã"].tolist()
    )

    st.session_state["selected_symbol"] = chosen
    st.success(f"Đã chọn {chosen} – chuyển sang TAB Soi chi tiết")

# ================== TAB 1: DETAIL ==================
with tab1:
    symbol = st.session_state["selected_symbol"]
    st.subheader(f"🔍 Phân tích chi tiết: {symbol}")

    df = load_data(symbol)

    if df.empty or len(df) < 50:
        st.error("Không đủ dữ liệu.")
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
    last = df.iloc[-1]

    st.markdown("### 📌 Phân tích nhanh")

    if last["Close"] > last["MA20"] > last["MA50"] and last["RSI"] < 70:
        st.success("✅ XU HƯỚNG TĂNG – CÓ THỂ MUA")
    elif last["RSI"] >= 70:
        st.warning("⚠️ QUÁ MUA – CẨN TRỌNG")
    else:
        st.info("⏳ CHƯA RÕ – THEO DÕI")

    st.write(f"**Giá:** {round(last['Close'],2)}")
    st.write(f"**RSI:** {round(last['RSI'],2)}")
