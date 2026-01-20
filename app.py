import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ================== CONFIG ==================
st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("📊 PRO TRADER – AUTO STOCK SCANNER")

# ================== LOAD SYMBOLS ==================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df.iloc[:, 0].dropna().unique().tolist()

# ================== LOAD PRICE ==================
@st.cache_data
def load_price(symbol):
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

    return df.dropna()

# ================== CHECK MA CROSS ==================
def recent_ma_cross(df, lookback=7):
    recent = df.tail(lookback + 1)
    prev = recent.iloc[:-1]
    last = recent.iloc[-1]

    cross = (
        (prev["MA20"] <= prev["MA50"]).any()
        and last["MA20"] > last["MA50"]
    )
    return cross

# ================== SCORING ==================
def calc_score(df):
    last = df.iloc[-1]

    score = 0
    reasons = []

    if last["MA20"] > last["MA50"]:
        score += 30
        reasons.append("MA20 > MA50")

    if recent_ma_cross(df):
        score += 30
        reasons.append("MA20 vừa cắt lên MA50")

    dist = (last["Close"] - last["MA20"]) / last["MA20"] * 100
    if dist <= 8:
        score += 20
        reasons.append("Giá chưa xa MA20")

    if last["RSI"] < 70:
        score += 20
        reasons.append("RSI chưa quá mua")

    return score, round(dist, 2), " | ".join(reasons)

# ================== AUTO SCAN ==================
if st.button("🔍 QUÉT TOÀN BỘ DANH SÁCH"):
    symbols = load_symbols()
    results = []

    progress = st.progress(0)

    for i, sym in enumerate(symbols):
        df = load_price(sym)
        if df.empty or len(df) < 60:
            continue

        df = add_indicators(df)

        score, dist, reason = calc_score(df)
        last = df.iloc[-1]

        if score >= 70:
            signal = "🟢 MUA SỚM"
        elif score >= 50:
            signal = "🟡 THEO DÕI"
        else:
            signal = "🔴 BỎ QUA"

        results.append({
            "Mã": sym,
            "Giá": round(last["Close"], 2),
            "RSI": round(last["RSI"], 1),
            "MA20 > MA50": "✅" if last["MA20"] > last["MA50"] else "❌",
            "Cách MA20 (%)": dist,
            "Điểm": score,
            "Khuyến nghị": signal,
            "Lý do": reason
        })

        progress.progress((i + 1) / len(symbols))

    if results:
        df_result = pd.DataFrame(results).sort_values("Điểm", ascending=False)
        st.success(f"✅ Hoàn tất quét {len(df_result)} mã đạt điều kiện")
        st.dataframe(df_result, use_container_width=True)

        st.subheader("🔥 TOP 10 ĐANG VÀO SÓNG")
        st.dataframe(df_result.head(10), use_container_width=True)
    else:
        st.warning("❌ Không có mã nào đạt điều kiện hiện tại")

# ================== VIEW 1 MÃ ==================
st.divider()
st.subheader("🔍 SOI KỸ 1 MÃ")

symbol_view = st.text_input("Nhập mã để soi kỹ", "VNM.VN")
df_view = load_price(symbol_view)

if not df_view.empty and len(df_view) >= 60:
    df_view = add_indicators(df_view)

    fig = go.Figure()
    fig.add_candlestick(
        x=df_view.index,
        open=df_view["Open"],
        high=df_view["High"],
        low=df_view["Low"],
        close=df_view["Close"],
        name="Giá"
    )
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df_view.index, y=df_view["MA50"], name="MA50"))

    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    last = df_view.iloc[-1]
    st.write(f"RSI: **{round(last['RSI'],1)}**")
    st.write(f"MA20 > MA50: **{'Có' if last['MA20'] > last['MA50'] else 'Không'}**")
else:
    st.info("Chưa đủ dữ liệu để phân tích")
