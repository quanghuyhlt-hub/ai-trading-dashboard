import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================= CONFIG =================
st.set_page_config(page_title="Pro Trader – Trade Decision", layout="wide")
st.title("🔥 PRO TRADER – BẢNG QUYẾT ĐỊNH VÀO LỆNH")

# ================= STOCK LIST (DEMO) =================
VN_STOCKS = [
    "VNM.VN","HPG.VN","FPT.VN","MWG.VN","VIC.VN",
    "VCB.VN","CTG.VN","BID.VN","SSI.VN","VND.VN",
    "PNJ.VN","GMD.VN","POW.VN","STB.VN","TCB.VN"
]

# ================= DATA =================
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

# ================= TRADE DECISION =================
def trade_decision(df):
    last = df.iloc[-1]

    entry = last["Close"]
    sl = last["MA50"]

    if entry <= sl:
        return None

    risk = entry - sl
    tp = entry + risk * 2
    rr = (tp - entry) / risk

    if rr >= 1.5:
        verdict = "✅ KÈO ĐẸP – VÀO ĐƯỢC"
    else:
        verdict = "❌ RR XẤU – BỎ"

    return {
        "Entry": round(entry,2),
        "Stop Loss": round(sl,2),
        "Take Profit": round(tp,2),
        "RR": round(rr,2),
        "Kết luận": verdict
    }

# ================= UI =================
st.subheader("📊 AUTO SCAN – QUYẾT ĐỊNH TRADER")

if st.button("🚀 QUÉT & LẬP KÈO"):
    rows = []

    with st.spinner("Đang tính toán kèo..."):
        for sym in VN_STOCKS:
            df = load_data(sym)
            if df.empty or len(df) < 60:
                continue

            df = add_indicators(df)
            res = trade_decision(df)

            if res:
                rows.append({
                    "Mã": sym,
                    **res
                })

    if rows:
        df_out = pd.DataFrame(rows)
        st.dataframe(df_out, use_container_width=True)
    else:
        st.warning("Không có kèo đạt RR tối thiểu.")
