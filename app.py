import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Trading Dashboard")

# ================== STOCK LIST (DEMO) ==================
ALL_SYMBOLS = ["VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN", "SHS.VN", "PVS.VN"]

# ================== DATA ==================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="9mo", interval="1d", progress=False)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df

def add_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["VOL_RATIO"] = df["Volume"] / df["Volume"].rolling(20).mean()
    df.dropna(inplace=True)
    return df

# ================== AI MODEL ==================
def train_ai(df):
    df["FUTURE_RETURN"] = df["Close"].shift(-10) / df["Close"] - 1
    df["TARGET"] = (df["FUTURE_RETURN"] > 0.05).astype(int)

    features = ["MA20", "MA50", "RSI", "VOL_RATIO"]
    X = df[features]
    y = df["TARGET"]

    model = LogisticRegression()
    model.fit(X, y)
    return model

# ================== SESSION ==================
if "selected_symbol" not in st.session_state:
    st.session_state["selected_symbol"] = "VNM.VN"

tab1, tab2 = st.tabs(["🔍 Soi chi tiết", "📡 Auto Scan"])

# ================== TAB 2 ==================
with tab2:
    rows = []
    for sym in ALL_SYMBOLS:
        df = load_data(sym)
        if df.empty or len(df) < 80:
            continue
        df = add_indicators(df)
        rows.append({
            "Mã": sym,
            "Giá": round(df["Close"].iloc[-1],2),
            "RSI": round(df["RSI"].iloc[-1],2)
        })
    scan_df = pd.DataFrame(rows)
    st.dataframe(scan_df, use_container_width=True)

    choice = st.selectbox("Chọn mã để soi:", scan_df["Mã"])
    st.session_state["selected_symbol"] = choice

# ================== TAB 1 ==================
with tab1:
    symbol = st.session_state["selected_symbol"]
    st.subheader(f"🔍 {symbol}")

    df = load_data(symbol)
    df = add_indicators(df)

    model = train_ai(df)
    latest = df.iloc[-1][["MA20", "MA50", "RSI", "VOL_RATIO"]].values.reshape(1, -1)
    prob = model.predict_proba(latest)[0][1] * 100

    fig = go.Figure()
    fig.add_candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )
    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🤖 AI Probability")
    st.metric("Xác suất tăng ≥5% (10 phiên)", f"{prob:.1f}%")

    if prob >= 65:
        st.success("🔥 AI ĐÁNH GIÁ CAO – PHÙ HỢP ĐÁNH TREND")
    elif prob >= 55:
        st.info("👀 TRUNG TÍNH – THEO DÕI")
    else:
        st.warning("⚠️ RỦI RO – KHÔNG ƯU TIÊN")
