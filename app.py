import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ======================
# CONFIG
# ======================
st.set_page_config(page_title="Level X – Pro Trader Scanner", layout="wide")

# ======================
# INIT SESSION STATE
# ======================
if "results" not in st.session_state:
    st.session_state.results = []

# ======================
# DATA FUNCTIONS
# ======================
def load_data(symbol, period="6mo"):
    df = yf.download(symbol, period=period, progress=False)
    if df.empty:
        return None

    df = df.reset_index()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Vol_MA20"] = df["Volume"].rolling(20).mean()

    return df.dropna()

# ======================
# SCORING LOGIC
# ======================
def analyze_stock(symbol):
    df = load_data(symbol)
    if df is None or len(df) < 60:
        return None

    last = df.iloc[-1]

    score = 0
    reasons = []

    # MA20 > MA50
    if last["MA20"] > last["MA50"]:
        score += 30
        reasons.append("MA20 nằm trên MA50")

    # Giá gần MA20
    dist_ma20 = (last["Close"] - last["MA20"]) / last["MA20"] * 100
    if abs(dist_ma20) < 3:
        score += 20
        reasons.append("Giá sát MA20")

    # RSI khỏe
    if 50 < last["RSI"] < 70:
        score += 20
        reasons.append("RSI khỏe")

    # Volume xác nhận
    if last["Volume"] > last["Vol_MA20"]:
        score += 20
        reasons.append("Volume vượt MA20")

    # Không quá nóng
    if dist_ma20 < 8:
        score += 10

    # Nhận định
    if score >= 70:
        view = "🟢 NÊN THEO DÕI MUA"
    elif score >= 50:
        view = "🟡 QUAN SÁT"
    else:
        view = "🔴 LOẠI"

    return {
        "Mã": symbol,
        "Giá": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "Cách MA20 (%)": round(dist_ma20, 2),
        "Volume > MA20": "✅" if last["Volume"] > last["Vol_MA20"] else "❌",
        "Score": score,
        "Nhận định": view,
        "Lý do": ", ".join(reasons),
        "DF": df
    }

# ======================
# UI
# ======================
st.title("🚀 Level X – Pro Trader Scanner")

symbols = st.multiselect(
    "Chọn danh sách mã (demo – có thể thay bằng full HOSE/HNX)",
    ["VNM.VN", "HPG.VN", "FPT.VN", "MWG.VN", "SSI.VN", "PNJ.VN"],
    default=["VNM.VN", "HPG.VN", "FPT.VN"]
)

if st.button("🚀 AUTO SCAN PRO"):
    results = []
    with st.spinner("Đang quét..."):
        for s in symbols:
            r = analyze_stock(s)
            if r:
                results.append(r)

    st.session_state.results = results

# ======================
# RESULT TABLE
# ======================
results = st.session_state.results

if results:
    st.subheader("📊 Kết quả Auto Scan")

    df_table = pd.DataFrame([
        {k: v for k, v in r.items() if k not in ["DF", "Lý do"]}
        for r in results
    ]).sort_values("Score", ascending=False)

    st.dataframe(df_table, use_container_width=True)

    # ======================
    # DETAIL VIEW
    # ======================
    st.subheader("📈 Phân tích chi tiết Trader-ready")

    pick = st.selectbox(
        "Chọn mã",
        [r["Mã"] for r in results]
    )

    r = next(x for x in results if x["Mã"] == pick)
    df = r["DF"]

    st.line_chart(df.set_index("Date")[["Close", "MA20", "MA50"]])

    last = df.iloc[-1]
    entry = last["Close"]
    stop = last["MA20"] * 0.97
    target = entry + 2 * (entry - stop)

    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 Entry", round(entry, 2))
    c2.metric("🛑 Stoploss", round(stop, 2))
    c3.metric("🚀 Target", round(target, 2))

    st.success(f"📌 Khuyến nghị: {r['Nhận định']}")
    st.info(f"📎 Cơ sở: {r['Lý do']}")

else:
    st.info("👉 Chọn mã và bấm **AUTO SCAN PRO** để bắt đầu.")
