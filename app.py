import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="AI Stock Scanner", layout="wide")

# =========================
# FUNCTIONS
# =========================

def SMA(series, window):
    return series.rolling(window).mean()

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def load_data(symbol, days=200):
    df = yf.download(symbol, period=f"{days}d", progress=False)
    if df.empty:
        return None
    df = df.reset_index()
    return df

def analyze_stock(symbol):
    df = load_data(symbol)
    if df is None or len(df) < 60:
        return None

    df["MA20"] = SMA(df["Close"], 20)
    df["MA50"] = SMA(df["Close"], 50)
    df["RSI"] = RSI(df["Close"], 14)
    df["VolMA20"] = SMA(df["Volume"], 20)

    last = df.iloc[-1]

    conditions = {
        "Giá > MA20": last["Close"] > last["MA20"],
        "MA20 > MA50": last["MA20"] > last["MA50"],
        "RSI > 50": last["RSI"] > 50,
        "RSI < 70": last["RSI"] < 70,
        "Volume > VolMA20": last["Volume"] > last["VolMA20"],
    }

    score = sum(conditions.values())

    result = {
        "Mã": symbol,
        "Giá hiện tại": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "Score": score,
    }

    for k, v in conditions.items():
        result[k] = "✅" if v else "❌"

    return result

# =========================
# UI
# =========================

st.title("📈 AI Trading Scanner – Decision Support")

st.markdown("""
Scan cổ phiếu theo **nhiều điều kiện kỹ thuật**  
👉 Không phán BUY/SELL ngu học  
👉 **Cho bảng điều kiện để con người quyết**
""")

symbols_input = st.text_area(
    "Nhập danh sách mã (mỗi mã 1 dòng – ví dụ: AAPL, MSFT, NVDA)",
    height=150
)

if st.button("🚀 Scan ngay"):
    symbols = [s.strip().upper() for s in symbols_input.splitlines() if s.strip()]

    if not symbols:
        st.warning("Nhập mã trước đã sếp ơi 😅")
    else:
        results = []

        with st.spinner("Đang scan..."):
            for sym in symbols:
                r = analyze_stock(sym)
                if r:
                    results.append(r)

        if not results:
            st.error("Không mã nào đủ dữ liệu")
        else:
            df_result = pd.DataFrame(results)
            df_result = df_result.sort_values("Score", ascending=False)

            st.subheader("📊 BẢNG HỖ TRỢ QUYẾT ĐỊNH")
            st.dataframe(df_result, use_container_width=True)

            st.markdown("""
### 🧠 Cách đọc bảng
- **Score càng cao → càng nhiều điều kiện ủng hộ**
- ❌ xuất hiện nhiều → bỏ qua hoặc chờ
- Đây là **decision-support**, không phải thầy bói
""")
