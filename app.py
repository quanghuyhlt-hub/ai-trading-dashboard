import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================= CONFIG =================
st.set_page_config(page_title="Level X Stock Scanner", layout="wide")
st.title("📊 Level X – Bộ lọc cổ phiếu vào sóng")

# ================= DATA =================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty or len(df) < 60:
        return pd.DataFrame()

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)

    # Indicators
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["Vol_MA20"] = df["Volume"].rolling(20).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================= LOGIC =================
def days_since_cross(df):
    cross = df["MA20"] > df["MA50"]
    cross_idx = np.where(cross & ~cross.shift(1).fillna(False))[0]
    if len(cross_idx) == 0:
        return None
    return len(df) - cross_idx[-1] - 1

def calc_score(last, days):
    score = 0

    if last["MA20"] > last["MA50"]:
        score += 20
    if days is not None and days <= 5:
        score += 25
    if last["Close"] > last["MA20"]:
        score += 15

    dist = (last["Close"] - last["MA20"]) / last["MA20"] * 100
    if dist < 5:
        score += 20

    if last["RSI"] < 70:
        score += 10
    if last["Volume"] > last["Vol_MA20"]:
        score += 10

    return score, round(dist, 2)

# ================= TABS =================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# ================= TAB 1 =================
with tab1:
    symbol = st.text_input("Nhập mã (VD: HPG.VN, FPT.VN)", "HPG.VN")
    df = load_data(symbol)

    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    last = df.iloc[-1]
    days = days_since_cross(df)
    score, dist = calc_score(last, days)

    st.metric("Giá hiện tại", round(float(last["Close"]), 2))
    st.metric("RSI", round(float(last["RSI"]), 2))
    st.metric("Score", score)

    if score >= 80:
        st.success("🟢 NÊN THEO DÕI / CANH MUA")
    elif score >= 65:
        st.info("🟡 QUAN SÁT")
    else:
        st.warning("🔴 CHƯA ƯU TIÊN")

# ================= TAB 2 =================
with tab2:
    st.subheader("🧠 AUTO SCAN – Cổ phiếu vào sóng sớm")

    symbols = [
        "HPG.VN","FPT.VN","MWG.VN","VNM.VN","PNJ.VN",
        "GMD.VN","SSI.VN","VND.VN","POW.VN","VIC.VN"
    ]

    rows = []

    for sym in symbols:
        df = load_data(sym)
        if df.empty:
            continue

        last = df.iloc[-1]
        days = days_since_cross(df)
        score, dist = calc_score(last, days)

        rows.append({
            "Mã": sym,
            "Giá": round(float(last["Close"]), 2),
            "RSI": round(float(last["RSI"]), 1),
            "Phiên từ MA20 cắt MA50": days,
            "Cách MA20 (%)": dist,
            "Volume > MA20": "✅" if last["Volume"] > last["Vol_MA20"] else "❌",
            "Score": score,
            "Nhận định": "NÊN THEO DÕI" if score >= 80 else "QUAN SÁT"
        })

    if rows:
        st.dataframe(pd.DataFrame(rows).sort_values("Score", ascending=False),
                     use_container_width=True)
    else:
        st.info("Không có mã phù hợp.")
