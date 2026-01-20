import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Pro Trader Scanner", layout="wide")
st.title("🔥 Pro Trader Scanner – MA20 x MA50 + Volume + RSI")

# =========================
# LOAD SYMBOL LIST
# =========================
@st.cache_data(ttl=3600)
def load_symbols():
    df = pd.read_csv("stocks.csv")
    return df["symbol"].dropna().unique().tolist()

# =========================
# FETCH DATA
# =========================
@st.cache_data(ttl=3600)
def fetch_price(symbol):
    df = yf.download(symbol, period="1y", interval="1d", progress=False)
    if df.empty or len(df) < 220:
        return None
    return df

# =========================
# INDICATORS
# =========================
def compute_indicators(df):
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    # ✅ RSI FIX – CHUẨN
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# =========================
# CONDITIONS
# =========================
def check_conditions(df):
    prev = df.iloc[-2]
    curr = df.iloc[-1]

    ma_cross = prev["MA20"] <= prev["MA50"] and curr["MA20"] > curr["MA50"]
    price_above_ma200 = curr["Close"] > curr["MA200"]
    rsi_ok = curr["RSI"] > 50
    volume_breakout = curr["Volume"] > 1.5 * curr["VOL_MA20"]

    return ma_cross and price_above_ma200 and rsi_ok and volume_breakout

# =========================
# MAIN SCAN
# =========================
symbols = load_symbols()
results = []

with st.spinner("🚀 Scanning market..."):
    for sym in symbols:
        df = fetch_price(sym)
        if df is None:
            continue

        df = compute_indicators(df)

        if check_conditions(df):
            last = df.iloc[-1]
            results.append({
                "Symbol": sym,
                "Close": round(last["Close"], 2),
                "MA20": round(last["MA20"], 2),
                "MA50": round(last["MA50"], 2),
                "MA200": round(last["MA200"], 2),
                "RSI": round(last["RSI"], 1),
                "Volume": int(last["Volume"]),
                "Vol x MA20": round(last["Volume"] / last["VOL_MA20"], 2)
            })

# =========================
# DISPLAY
# =========================
st.subheader("✅ Cổ phiếu đạt điều kiện")

if results:
    st.dataframe(
        pd.DataFrame(results).sort_values("Vol x MA20", ascending=False),
        use_container_width=True
    )
else:
    st.warning("Không có mã nào đạt điều kiện hôm nay.")
