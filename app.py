import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Level X – Trading Dashboard", layout="wide")
st.title("📊 Level X – Trading Dashboard")

# ======================
# DATA
# ======================
def fetch_price(symbol):
    df = yf.Ticker(symbol).history(period="1y")
    if df.empty:
        return df
    df = df.reset_index()
    return df


@st.cache_data
def load_data(symbol):
    df = fetch_price(symbol)
    if df.empty:
        return df

    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    return df


# ======================
# CORE LOGIC
# ======================
def detect_cross(df, lookback):
    df = df.dropna().copy()
    df["prev_MA20"] = df["MA20"].shift(1)
    df["prev_MA50"] = df["MA50"].shift(1)

    recent = df.tail(lookback)
    cross = recent[
        (recent["prev_MA20"] < recent["prev_MA50"]) &
        (recent["MA20"] > recent["MA50"])
    ]
    return None if cross.empty else cross.iloc[-1]


def slope(series, n=3):
    return series.iloc[-1] - series.iloc[-n]


def ai_score(df, cross_row, lookback):
    score = 0
    last = df.iloc[-1]

    # 1. MA cross timing
    cross_idx = df.index.get_loc(cross_row.name)
    bars_ago = len(df) - cross_idx - 1
    if bars_ago <= 3:
        score += 30
    elif bars_ago <= 5:
        score += 20
    else:
        score += 10

    # 2. Price gap
    gap = (last["Close"] - cross_row["Close"]) / cross_row["Close"]
    if gap <= 0.05:
        score += 30
    elif gap <= 0.10:
        score += 20
    elif gap <= 0.15:
        score += 10

    # 3. Volume
    if last["Volume"] > 2 * last["VOL_MA20"]:
        score += 20
    elif last["Volume"] > 1.5 * last["VOL_MA20"]:
        score += 10

    # 4. MA slope
    if slope(df["MA20"]) > 0 and slope(df["MA50"]) > 0:
        score += 20
    elif slope(df["MA20"]) > 0:
        score += 10

    return score


def entry_label(score):
    if score >= 80:
        return "🔥 Entry sớm"
    elif score >= 60:
        return "🟡 Entry trung bình"
    else:
        return "❌ Entry muộn"


# ======================
# TABS
# ======================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# ======================
# TAB 1
# ======================
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu", "VNM.VN")
    df = load_data(symbol)

    if not df.empty:
        cross = detect_cross(df, 10)
        if cross is not None:
            score = ai_score(df, cross, 10)
            st.metric("AI Score", score)
            st.write("👉", entry_label(score))
        else:
            st.warning("Chưa có MA20 cắt MA50")

        st.dataframe(df.tail(10))


# ======================
# TAB 2 – AUTO SCAN
# ======================
with tab2:
    symbols = st.text_area(
        "Danh sách mã (mỗi dòng 1 mã)",
        "VNM.VN\nHPG.VN\nFPT.VN\nVCB.VN\nMWG.VN"
    )

    lookback = st.slider("Lookback MA cross", 3, 10, 5)

    if st.button("🚀 SCAN"):
        results = []

        for sym in symbols.splitlines():
            sym = sym.strip()
            if not sym:
                continue

            df = load_data(sym)
            if df.empty:
                continue

            cross = detect_cross(df, lookback)
            if cross is None:
                continue

            score = ai_score(df, cross, lookback)

            results.append({
                "Mã": sym,
                "Giá hiện tại": round(df.iloc[-1]["Close"], 2),
                "AI Score": score,
                "Entry": entry_label(score)
            })

        if results:
            df_rs = pd.DataFrame(results).sort_values("AI Score", ascending=False)
            st.success("✅ KẾT QUẢ AUTO SCAN")
            st.dataframe(df_rs)
        else:
            st.warning("❌ Không có mã đạt chuẩn")
