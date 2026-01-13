import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ================= CONFIG =================
st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("📡 PRO TRADER – FULL MARKET SCAN + CHART")

# ================= LOAD STOCK LIST =================
@st.cache_data
def load_stock_list():
    return pd.read_csv("stocks.csv")["symbol"].dropna().tolist()

# ================= LOAD DATA =================
@st.cache_data
def load_data(symbol):
    df = yf.download(symbol, period="8mo", interval="1d", progress=False)

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open","High","Low","Close","Volume"]]
    df.dropna(inplace=True)
    return df

# ================= INDICATORS =================
def add_indicators(df):
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# ================= STRATEGY =================
def evaluate_stock(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Điều kiện lõi
    if last["Close"] <= last["MA50"]:
        return None

    if not (prev["MA20"] < prev["MA50"] and last["MA20"] > last["MA50"]):
        return None

    risk = last["Close"] - last["MA50"]
    tp = last["Close"] + risk * 2
    rr = (tp - last["Close"]) / risk

    if rr < 1.8:
        return None

    if rr >= 2.5 and 55 <= last["RSI"] <= 70:
        tier = "ALL-IN KỸ THUẬT"
    elif rr >= 2.0:
        tier = "CHỦ LỰC"
    else:
        tier = "THĂM DÒ"

    return {
        "Mã": "",
        "Entry": round(last["Close"],2),
        "Stop Loss": round(last["MA50"],2),
        "Take Profit": round(tp,2),
        "RR": round(rr,2),
        "RSI": round(last["RSI"],1),
        "Khuyến nghị": tier
    }

# ================= UI =================
stock_list = load_stock_list()

if "scan_result" not in st.session_state:
    st.session_state.scan_result = pd.DataFrame()

# ---------- SCAN ----------
if st.button("📊 QUÉT TOÀN BỘ THỊ TRƯỜNG"):
    results = []

    with st.spinner(f"Đang quét {len(stock_list)} mã..."):
        for sym in stock_list:
            df = load_data(sym)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            res = evaluate_stock(df)

            if res:
                res["Mã"] = sym
                results.append(res)

    if results:
        st.session_state.scan_result = pd.DataFrame(results)
        st.success(f"✅ Tìm được {len(results)} mã đạt chuẩn Trader")
    else:
        st.warning("Không có mã nào đạt tiêu chí hiện tại.")

# ---------- TABLE ----------
if not st.session_state.scan_result.empty:
    st.subheader("📋 DANH SÁCH MÃ ĐẠT CHUẨN")
    st.dataframe(st.session_state.scan_result, use_container_width=True)

    # ---------- SELECT STOCK ----------
    selected = st.selectbox(
        "👉 Chọn mã để xem chi tiết chart & vùng vào lệnh",
        st.session_state.scan_result["Mã"]
    )

    df_chart = add_indicators(load_data(selected))
    last = df_chart.iloc[-1]

    # ---------- CHART ----------
    fig = go.Figure()

    fig.add_candlestick(
        x=df_chart.index,
        open=df_chart["Open"],
        high=df_chart["High"],
        low=df_chart["Low"],
        close=df_chart["Close"],
        name="Price"
    )

    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA50"], name="MA50"))

    # Entry / SL / TP
    entry = last["Close"]
    sl = last["MA50"]
    tp = entry + (entry - sl) * 2

    fig.add_hline(y=entry, line_dash="dash", annotation_text="ENTRY")
    fig.add_hline(y=sl, line_dash="dot", annotation_text="STOP LOSS")
    fig.add_hline(y=tp, line_dash="dash", annotation_text="TAKE PROFIT")

    fig.update_layout(height=650)
    st.plotly_chart(fig, use_container_width=True)

    # ---------- RECOMMEND ----------
    st.subheader("🧠 KHUYẾN NGHỊ GIAO DỊCH")
    st.write(f"**Mã:** {selected}")
    st.write(f"**Entry:** {round(entry,2)}")
    st.write(f"**Stop Loss:** {round(sl,2)}")
    st.write(f"**Take Profit:** {round(tp,2)}")
    st.write(f"**RSI:** {round(last['RSI'],1)}")

    if last["RSI"] < 70:
        st.success("📈 Xu hướng khỏe – có thể vào theo kế hoạch")
    else:
        st.warning("⚠️ RSI cao – hạn chế FOMO, chờ retest")
