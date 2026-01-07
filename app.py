import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Level X Trading Dashboard", layout="wide")
st.title("📊 Level X – Stock Trading Dashboard")tab1 with tab1:
    # (giữ nguyên toàn bộ code phân tích 1 mã hiện tại)
, tab2 = st.tabs(["📊 Phân tích chi tiết", "🤖 Auto Scan"])with tab2:
    st.subheader("🤖 Auto Scan – Tín hiệu MUA")

    market = st.selectbox("Chọn sàn", ["HOSE", "HNX"])
    symbols = VN_STOCKS[market]

    results = []

    for sym in symbols:
        df_scan = load_data(sym)
        if df_scan.empty or len(df_scan) < 50:
            continue

        # Indicator
        df_scan["MA20"] = df_scan["Close"].rolling(20).mean()
        df_scan["MA50"] = df_scan["Close"].rolling(50).mean()

        delta = df_scan["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df_scan["RSI"] = 100 - (100 / (1 + rs))

        df_scan.dropna(inplace=True)
        last = df_scan.iloc[-1]

        if last["Close"] > last["MA20"] > last["MA50"] and last["RSI"] < 70:
            results.append({
                "Mã": sym,
                "Giá": round(last["Close"], 2),
                "RSI": round(last["RSI"], 2),
                "Xu hướng": "Tăng",
                "Khuyến nghị": "MUA"
            })

    if results:
        st.dataframe(pd.DataFrame(results))
    else:
        st.info("Chưa có mã nào thỏa điều kiện hôm nay.")

VN_STOCKS = {
    "HOSE": ["VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "VIC.VN"],
    "HNX": ["SHS.VN", "PVS.VN", "IDC.VN"]
}
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    # 🔥 FIX: flatten multi-index columns nếu có
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)

    return df

symbol = st.text_input(
    "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
    "VNM.VN"
)

df = load_data(symbol)

# 🚨 CHẶN LỖI TUYỆT ĐỐI
if df.empty or len(df) < 50:
    st.error("❌ Không lấy được dữ liệu hoặc dữ liệu không đủ.")
    st.stop()

# ===== INDICATORS (TỰ TÍNH – KHÔNG TA) =====

# MA
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()

# RSI
delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12, adjust=False).mean()
ema26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = ema12 - ema26
df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()


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

# ===== SIGNAL =====
st.subheader("📌 Phân tích nhanh")

last_close = float(df["Close"].iloc[-1])
ma20 = float(df["MA20"].iloc[-1])
ma50 = float(df["MA50"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])

if last_close > ma20 > ma50 and rsi < 70:
    st.success("✅ TÍN HIỆU: MUA – Xu hướng tăng khỏe")
elif rsi >= 70:
    st.warning("⚠️ QUÁ MUA – Dễ điều chỉnh")
else:
    st.info("⏳ CHƯA RÕ – Nên quan sát")

st.write(f"RSI: {round(rsi, 2)}")
st.write(f"MACD: {round(macd, 2)}")

