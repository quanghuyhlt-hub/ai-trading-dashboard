import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# ================== CONFIG ==================
st.set_page_config(
    page_title="Level X Trading Dashboard",
    layout="wide"
)

st.title("📊 Level X – Trading Dashboard")

# ================== DATA LOADER ==================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return df

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df

# ================== TABS ==================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# =================================================
# TAB 1 – PHÂN TÍCH 1 MÃ
# =================================================
with tab1:
    symbol = st.text_input(
        "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
        "VNM.VN"
    )

    df = load_data(symbol)

    if df.empty or len(df) < 50:
        st.error("❌ Không lấy được dữ liệu hoặc dữ liệu không đủ.")
        st.stop()

    # ===== INDICATORS =====
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

    # ===== PHÂN TÍCH NHANH (FIX HOÀN TOÀN SERIES BUG) =====
    st.subheader("📌 Phân tích nhanh")

    last_close = float(df["Close"].iloc[-1])
    ma20 = float(df["MA20"].iloc[-1])
    ma50 = float(df["MA50"].iloc[-1])
    rsi = float(df["RSI"].iloc[-1])
    macd = float(df["MACD"].iloc[-1])

    score = 0
    if last_close > ma20:
        score += 25
    if ma20 > ma50:
        score += 25
    if rsi < 70:
        score += 25
    if macd > 0:
        score += 25

    if score >= 75:
        st.success("✅ TÍN HIỆU: MUA – Xu hướng tăng mạnh")
    elif score >= 50:
        st.info("⏳ THEO DÕI – Đang hình thành xu hướng")
    else:
        st.warning("⚠️ CHƯA ĐẸP – Tránh vội vàng")

    st.write(f"🔢 Trend Score: **{score}%**")
    st.write(f"RSI: {round(rsi, 2)}")
    st.write(f"MACD: {round(macd, 2)}")

# =================================================
# TAB 2 – AUTO SCAN (LEVEL X++)
# =================================================
with tab2:
    st.subheader("🧠 AUTO SCAN – Quét toàn sàn cổ phiếu tiềm năng")

    # ===== DANH SÁCH FULL SÀN (DEMO – SẼ MỞ RỘNG 400 MÃ) =====
    HOSE = [
        "VNM.VN","HPG.VN","FPT.VN","MWG.VN","VIC.VN","SSI.VN","VND.VN",
        "PNJ.VN","GMD.VN","POW.VN","VCB.VN","BID.VN","CTG.VN","MBB.VN",
        "TCB.VN","VPB.VN","ACB.VN","HDB.VN","STB.VN"
    ]

    symbols = HOSE  # turn sau em bung full 400 mã

    results = []

    for sym in symbols:
        df_scan = load_data(sym)
        if df_scan.empty or len(df_scan) < 50:
            continue

        df_scan = df_scan.copy()

        df_scan["MA20"] = df_scan["Close"].rolling(20).mean()
        df_scan["MA50"] = df_scan["Close"].rolling(50).mean()
        df_scan["VOL_MA20"] = df_scan["Volume"].rolling(20).mean()

        delta = df_scan["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df_scan["RSI"] = 100 - (100 / (1 + rs))

        last = df_scan.iloc[-1]

        # ===== ĐIỀU KIỆN LỌC =====
        cond_price = last["Close"] > last["MA20"]
        cond_trend = last["MA20"] > last["MA50"]
        cond_rsi = 40 <= float(last["RSI"]) <= 65
        cond_vol = last["Volume"] > last["VOL_MA20"]

        score = sum([cond_price, cond_trend, cond_rsi, cond_vol]) * 25

        if score >= 75:
            results.append({
                "Mã": sym,
                "Giá": round(float(last["Close"]), 2),
                "RSI": round(float(last["RSI"]), 1),
                "Volume": int(last["Volume"]),
                "Trend Score (%)": score,
                "Khuyến nghị": "MUA / THEO DÕI SÁT"
            })

    if results:
        st.dataframe(
            pd.DataFrame(results).sort_values("Trend Score (%)", ascending=False),
            use_container_width=True
        )
    else:
        st.info("Chưa có cổ phiếu nào đủ chuẩn tại thời điểm này.")

    
       
