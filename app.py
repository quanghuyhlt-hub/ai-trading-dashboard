import yfinance as yf
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
def ai_probability(last, prev):
    score = 0

    # 1. Giá trên MA20
    if last["Close"] > last["MA20"]:
        score += 20

    # 2. Xu hướng
    if last["MA20"] > last["MA50"]:
        score += 20

    # 3. RSI đẹp
    if 45 <= last["RSI"] <= 60:
        score += 20
    elif 40 <= last["RSI"] <= 65:
        score += 10

    # 4. Volume
    if last["Volume"] > last["VOL_MA20"] * 1.3:
        score += 20
    elif last["Volume"] > last["VOL_MA20"]:
        score += 10

    # 5. Độ dốc MA20
    if last["MA20"] > prev["MA20"]:
        score += 20

    return min(score, 100)

# ================== CONFIG ==================
st.set_page_config(
    page_title="Level X Trading Dashboard",
    layout="wide"
)

st.title("📊 Level X – Trading Dashboard")

# ================== DATA LOADER ==================
@st.cache_data
def load_data(symbol):
    df = fetch_price_from_source(symbol)
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    return df


    # ===== MOVING AVERAGES =====
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["MA20_prev1"] = df["MA20"].shift(1)
    df["MA50_prev1"] = df["MA50"].shift(1)

    df["MA20_prev2"] = df["MA20"].shift(2)
    df["MA50_prev2"] = df["MA50"].shift(2)

    df["MA20_prev3"] = df["MA20"].shift(3)
    df["MA50_prev3"] = df["MA50"].shift(3)

    df["MA20_cross_3"] = (
        (df["MA20"] > df["MA50"]) &
        (
            (df["MA20_prev1"] <= df["MA50_prev1"]) |
            (df["MA20_prev2"] <= df["MA50_prev2"]) |
            (df["MA20_prev3"] <= df["MA50_prev3"])
        )
    )

    return df


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

    # ===== FULL DANH SÁCH HOSE + HNX (RÚT GỌN ĐẠI DIỆN – SCALE ĐƯỢC 400 MÃ) =====
    HOSE = [
        "VNM.VN","HPG.VN","FPT.VN","MWG.VN","VIC.VN","VCB.VN","BID.VN","CTG.VN",
        "TCB.VN","MBB.VN","VPB.VN","ACB.VN","HDB.VN","STB.VN","SSI.VN","VND.VN",
        "POW.VN","GMD.VN","PNJ.VN","SAB.VN","REE.VN","DXG.VN","DIG.VN","KBC.VN",
        "VRE.VN","BCM.VN","GAS.VN","PLX.VN","BVH.VN","MSN.VN"
    ]

    HNX = [
        "SHS.VN","PVS.VN","IDC.VN","CEO.VN","VCG.VN","L14.VN","TNG.VN","PLC.VN",
        "LAS.VN","DTD.VN","NBC.VN","BCC.VN"
    ]

    symbols = HOSE + HNX   # 👉 Chỉ cần mở rộng list này = đủ 400 mã

    results = []

for sym in symbols:
    df_scan = load_data(sym)

    if df_scan.empty or len(df_scan) < 50:
        continue

    df_scan["MA20"] = df_scan["Close"].rolling(20).mean()
    df_scan["MA50"] = df_scan["Close"].rolling(50).mean()

    delta = df_scan["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df_scan["RSI"] = 100 - (100 / (1 + rs))

    last = df_scan.iloc[-1]

    ai_score = 0
    if last["Close"] > last["MA20"]:
        ai_score += 25
    if last["MA20"] > last["MA50"]:
        ai_score += 25
    if last["RSI"] < 70:
        ai_score += 25
    if last["Close"] > last["MA50"]:
        ai_score += 25

    signal = "MUA" if ai_score >= 80 else "THEO DÕI"

    results.append({
    "Mã": symbol,
    "Giá": round(last["Close"], 2),
    "MA20": round(last["MA20"], 2),
    "MA50": round(last["MA50"], 2),
    "AI Score": ai_score,
    "Khuyến nghị": "MUA" if ai_score >= 80 else "THEO DÕI"
})
if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True)
else:
    st.info("Không có cổ phiếu đủ điều kiện hiện tại.")
st.write(df.tail(3)[["Close","MA20","MA50","MA20_cross_3"]])

