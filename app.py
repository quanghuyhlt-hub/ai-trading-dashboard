import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Level X – Trading Dashboard", layout="wide")

# =========================
# DATA
# =========================
@st.cache_data(ttl=3600)
def load_data(symbol):
    df = yf.download(symbol, period="6mo", interval="1d", progress=False)
    if df.empty:
        return None
    df = df.reset_index()
    return df

# =========================
# INDICATORS
# =========================
def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Vol_MA20"] = df["Volume"].rolling(20).mean()

    return df

# =========================
# MA CROSS LOGIC
# =========================
def count_days_since_cross(df):
    cross = (df["MA20"] > df["MA50"]) & (df["MA20"].shift(1) <= df["MA50"].shift(1))
    idx = np.where(cross)[0]
    if len(idx) == 0:
        return None
    return len(df) - idx[-1] - 1

# =========================
# SCORING
# =========================
def calc_score(row, days_from_cross):
    score = 0

    if row["MA20"] > row["MA50"]:
        score += 20

    if days_from_cross is not None and days_from_cross <= 5:
        score += 25

    dist = (row["Close"] - row["MA20"]) / row["MA20"] * 100
    if dist < 5:
        score += 20

    if row["RSI"] < 70:
        score += 15

    if row["Volume"] > row["Vol_MA20"]:
        score += 20

    return score, dist

def rating(score):
    if score >= 80:
        return "🟢 NÊN THEO DÕI / CANH MUA"
    if score >= 65:
        return "🟡 QUAN SÁT"
    return "🔴 KHÔNG ƯU TIÊN"

# =========================
# UI
# =========================
st.title("📊 Level X – Trading Dashboard")

tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# =========================
# TAB 1
# =========================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN)", "VNM.VN")

    df = load_data(symbol)
    if df is None:
        st.error("Không tải được dữ liệu")
    else:
        df = add_indicators(df)
        last = df.iloc[-1]
        days = count_days_since_cross(df)

        score, dist = calc_score(last, days)

        st.subheader(f"📌 {symbol}")
        st.write(f"**Giá:** {last['Close']:.2f}")
        st.write(f"**MA20 / MA50:** {last['MA20']:.2f} / {last['MA50']:.2f}")
        st.write(f"**RSI:** {last['RSI']:.1f}")
        st.write(f"**Cách MA20:** {dist:.2f}%")
        st.write(f"**Phiên từ MA20 cắt MA50:** {days}")
        st.write(f"**Score:** {score}")
        st.success(rating(score))

# =========================
# TAB 2 – AUTO SCAN
# =========================
with tab2:
    symbols = st.text_area(
        "Danh sách mã (mỗi dòng 1 mã – VD: VNM.VN)",
        "VNM.VN\nHPG.VN\nFPT.VN\nMWG.VN"
    )

    if st.button("🚀 BẮT ĐẦU SCAN"):
        results = []

        for sym in symbols.splitlines():
            sym = sym.strip()
            if sym == "":
                continue

            df = load_data(sym)
            if df is None:
                continue

            df = add_indicators(df)
            last = df.iloc[-1]
            days = count_days_since_cross(df)
            score, dist = calc_score(last, days)

            results.append({
                "Mã": sym,
                "Giá": round(last["Close"], 2),
                "MA20": round(last["MA20"], 2),
                "MA50": round(last["MA50"], 2),
                "Phiên từ Cross": days,
                "Cách MA20 (%)": round(dist, 2),
                "RSI": round(last["RSI"], 1),
                "Vol > MA20": "✅" if last["Volume"] > last["Vol_MA20"] else "❌",
                "Score": score,
                "Nhận định": rating(score)
            })

        if results:
            df_result = pd.DataFrame(results).sort_values("Score", ascending=False)
            st.dataframe(df_result, use_container_width=True)
        else:
            st.warning("Không có mã nào phù hợp")
