import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ================== CONFIG ==================
st.set_page_config(page_title="Pro Trader+ Scanner", layout="wide")
st.title("📈 PRO TRADER+ – AUTO STOCK SCANNER (VN)")

# ================== STOCK LIST ==================
# Demo subset – khi chạy ổn sẽ mở rộng lên ~400 mã
VN_STOCKS = [
    "VNM.VN","HPG.VN","FPT.VN","MWG.VN","VIC.VN","VCB.VN","CTG.VN","BID.VN",
    "SSI.VN","VND.VN","PNJ.VN","GMD.VN","POW.VN","STB.VN","TCB.VN","ACB.VN"
]

# ================== DATA ==================
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

# ================== INDICATORS ==================
def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    tr = pd.concat([
        df["High"] - df["Low"],
        abs(df["High"] - df["Close"].shift()),
        abs(df["Low"] - df["Close"].shift())
    ], axis=1).max(axis=1)

    df["ATR"] = tr.rolling(14).mean()

    return df

# ================== SCORING LOGIC ==================
def analyze_stock(df):
    last = df.iloc[-1]

    score = 0
    notes = []

    if last["Close"] > last["MA50"] > last["MA200"]:
        score += 30
        notes.append("Xu hướng tăng trung hạn")

    if last["MA20"] > last["MA50"]:
        score += 25
        notes.append("MA20 nằm trên MA50")

    if 50 <= last["RSI"] <= 65:
        score += 20
        notes.append("RSI khỏe, chưa quá mua")

    if last["Close"] > last["MA20"]:
        score += 15
        notes.append("Giá giữ trên MA20")

    if last["Volume"] > df["Volume"].rolling(20).mean().iloc[-1]:
        score += 10
        notes.append("Volume cải thiện")

    # Level
    if score >= 80:
        level = "🚀 PRO TRADER+"
    elif score >= 65:
        level = "✅ TRADER"
    elif score >= 50:
        level = "👀 WATCH"
    else:
        level = "❌ NO TRADE"

    # Risk
    entry = last["Close"]
    sl = entry - last["ATR"] * 1.5
    tp = entry + last["ATR"] * 3
    rr = (tp - entry) / (entry - sl) if entry > sl else np.nan

    return {
        "Level": level,
        "Score": score,
        "Entry": round(entry,2),
        "Stop Loss": round(sl,2),
        "Take Profit": round(tp,2),
        "RR": round(rr,2),
        "Nhận định": "; ".join(notes)
    }

# ================== UI ==================
st.subheader("🚀 AUTO SCAN TOÀN DANH SÁCH")

if st.button("🔍 QUÉT PRO TRADER+"):
    results = []

    with st.spinner("Đang quét thị trường..."):
        for sym in VN_STOCKS:
            df = load_data(sym)
            if df.empty or len(df) < 200:
                continue

            df = add_indicators(df)
            res = analyze_stock(df)

            results.append({
                "Mã": sym,
                **res
            })

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values("Score", ascending=False)

        st.success("✅ Quét xong – đây là các cơ hội đáng chú ý")
        st.dataframe(df_result, use_container_width=True)
    else:
        st.warning("Không tìm được mã phù hợp hiện tại")
