import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# ================== CONFIG ==================
st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Trading Dashboard")

# ================== DATA ==================
@st.cache_data
def load_data(symbol):
    def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26

    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    return df

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
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26

    return df

# ================== TABS ==================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# ================== TAB 1 ==================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN)", "VNM.VN")

    df = load_data(symbol)
    if df.empty or len(df) < 50:
        st.error("❌ Không đủ dữ liệu")
        st.stop()

    df = add_indicators(df)

    # ---- Chart
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
    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

    # ---- Analysis
    last = df.iloc[-1]

    score = 0
    if last["Close"] > last["MA20"]:
        score += 25
    if last["MA20"] > last["MA50"]:
        score += 25
    if last["RSI"] < 70:
        score += 25
    if last["MACD"] > 0:
        score += 25

    st.subheader("📌 Phân tích nhanh")

    if score >= 75:
        st.success("✅ MUA – Xu hướng tăng mạnh")
    elif score >= 50:
        st.info("⏳ THEO DÕI")
    else:
        st.warning("⚠️ CHƯA ĐẸP")

    st.write(f"Trend Score: **{score}%**")
    st.write(f"RSI: {round(last['RSI'],2)}")
    st.write(f"MACD: {round(last['MACD'],2)}")

# ================== TAB 2 ==================
with tab2:
    st.subheader("🧠 AUTO SCAN – SIÊU CỔ ĐANG VÀO TIỀN")

    symbols = [
        "VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN",
        "SSI.VN", "VND.VN", "PNJ.VN", "GMD.VN", "POW.VN"
    ]

    results = []

    for sym in symbols:
        df = load_data(sym)
        if df.empty or len(df) < 60:
            continue

        df = add_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0

        # Trend
        if last["Close"] > last["MA20"]:
            score += 15
        if last["MA20"] > last["MA50"]:
            score += 15

        # Momentum
        if last["RSI"] < 70 and last["RSI"] > prev["RSI"]:
            score += 20

        # MACD
        if last["MACD"] > 0:
            score += 15

        # Volume Breakout
        if last["Volume"] > 1.5 * last["VOL_MA20"]:
            score += 35

        # Label
        if score >= 80:
            label = "🚀 SIÊU CỔ – STRONG BUY"
        elif score >= 60:
            label = "✅ BUY"
        elif score >= 45:
            label = "👀 WATCH"
        else:
            label = "❌ BỎ QUA"

        results.append({
            "Mã": sym,
            "Giá": round(last["Close"], 2),
            "RSI": round(last["RSI"], 2),
            "Vol x MA20": round(last["Volume"] / last["VOL_MA20"], 2),
            "Score": score,
            "Trạng thái": label
        })

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values("Score", ascending=False)

        st.dataframe(df_result, use_container_width=True)

        st.success("👉 Ưu tiên soi các mã 🚀 SIÊU CỔ trong Tab 1")
    else:
        st.info("Hôm nay chưa có siêu cổ đúng chuẩn.")
