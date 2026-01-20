import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st

st.set_page_config(page_title="Stock Scanner", layout="wide")
st.title("📈 Stock Breakout Scanner")

# =========================
# Technical Indicators
# =========================

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def ADX(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr14 = tr.rolling(period).sum()
    plus_dm14 = plus_dm.rolling(period).sum()
    minus_dm14 = minus_dm.rolling(period).sum()

    plus_di = 100 * (plus_dm14 / tr14)
    minus_di = 100 * (minus_dm14 / tr14)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()

    return adx


# =========================
# Load stock list
# =========================

symbols = pd.read_csv("stocks.csv")["symbol"].dropna().unique().tolist()

st.write(f"🔍 Tổng số mã scan: **{len(symbols)}**")

results = []

progress = st.progress(0)

# =========================
# Scan loop
# =========================

for i, symbol in enumerate(symbols):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)

        if df.empty or len(df) < 200:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        df["MA20"] = close.rolling(20).mean()
        df["MA50"] = close.rolling(50).mean()
        df["MA200"] = close.rolling(200).mean()
        df["RSI"] = RSI(close)
        df["ADX"] = ADX(high, low, close)
        df["Vol_MA20"] = volume.rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # ===== CONDITIONS =====
        ma_cross_up = prev["MA20"] < prev["MA50"] and last["MA20"] > last["MA50"]
        price_above_ma200 = last["Close"] > last["MA200"]
        rsi_ok = last["RSI"] > 50
        vol_breakout = last["Volume"] > 1.5 * last["Vol_MA20"]
        adx_ok = last["ADX"] > 20

        if all([ma_cross_up, price_above_ma200, rsi_ok, vol_breakout, adx_ok]):
            results.append({
                "Symbol": symbol,
                "Close": round(last["Close"], 2),
                "RSI": round(last["RSI"], 1),
                "ADX": round(last["ADX"], 1),
                "Volume": int(last["Volume"]),
            })

    except Exception as e:
        pass

    progress.progress((i + 1) / len(symbols))

# =========================
# Result
# =========================

st.subheader("✅ KẾT QUẢ SCAN")

if results:
    result_df = pd.DataFrame(results).sort_values("ADX", ascending=False)
    st.dataframe(result_df, use_container_width=True)
else:
    st.warning("Không có mã nào thỏa điều kiện.")
