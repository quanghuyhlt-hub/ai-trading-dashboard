import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="VN Stock Pro Scanner",
    layout="wide"
)

st.title("📈 VN STOCK PRO SCANNER")
st.caption("Level: Trader → Pro Trader | One-file | No bullshit")

# ======================
# UTIL FUNCTIONS
# ======================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)

        if df.empty or len(df) < 50:
            return None

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        df["Vol_MA20"] = df["Volume"].rolling(20).mean()
        df["RSI"] = calculate_rsi(df["Close"])

        last = df.iloc[-1]

        close = float(last["Close"])
        ma20 = float(last["MA20"])
        ma50 = float(last["MA50"])
        rsi = float(last["RSI"])
        volume = float(last["Volume"])
        vol_ma20 = float(last["Vol_MA20"])

        score = 0
        reasons = []

        # === TREND ===
        if ma20 > ma50:
            score += 2
            reasons.append("MA20 > MA50 (Uptrend)")

        # === PRICE POSITION ===
        dist_ma20 = (close - ma20) / ma20 * 100
        if -2 <= dist_ma20 <= 4:
            score += 2
            reasons.append("Giá ở vùng đẹp quanh MA20")

        # === VOLUME ===
        if volume > vol_ma20:
            score += 1
            reasons.append("Volume > MA20 Volume")

        # === RSI ===
        if 50 <= rsi <= 65:
            score += 2
            reasons.append("RSI khỏe (50–65)")
        elif rsi < 40:
            reasons.append("RSI yếu")

        # === CLASSIFY ===
        if score >= 6:
            level = "🔥 STRONG BUY"
            action = "Có thể giải ngân 30–50%, ưu tiên breakout"
        elif score >= 4:
            level = "🟢 WATCHLIST"
            action = "Theo dõi, chờ xác nhận volume"
        else:
            level = "⚠️ NO TRADE"
            action = "Không nên vào lệnh"

        return {
            "Symbol": symbol,
            "Close": round(close, 2),
            "RSI": round(rsi, 1),
            "Score": score,
            "Level": level,
            "Recommendation": action,
            "Reason": ", ".join(reasons),
            "Data": df
        }

    except Exception as e:
        return None


def plot_chart(df, symbol):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA20"],
        name="MA20"
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["MA50"],
        name="MA50"
    ))

    fig.update_layout(
        title=f"{symbol} Price Chart",
        height=500,
        xaxis_rangeslider_visible=False
    )

    return fig


# ======================
# UI INPUT
# ======================
st.sidebar.header("⚙️ Scanner Settings")

symbols_input = st.sidebar.text_area(
    "Danh sách mã (phân cách bằng dấu phẩy)",
    value="VCB.VN, VNM.VN, FPT.VN, HPG.VN"
)

run_scan = st.sidebar.button("🚀 SCAN NOW")

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# ======================
# MAIN LOGIC
# ======================
if run_scan:
    results = []

    with st.spinner("Đang quét thị trường..."):
        for sym in symbols:
            res = analyze_stock(sym)
            if res:
                results.append(res)

    if not results:
        st.error("Không có mã hợp lệ")
    else:
        df_result = pd.DataFrame(results).drop(columns=["Data"])

        st.subheader("📊 KẾT QUẢ SCAN")
        st.dataframe(df_result, use_container_width=True)

        # ===== STRONG BUY =====
        strong = [r for r in results if r["Level"] == "🔥 STRONG BUY"]

        if strong:
            st.subheader("🔥 STRONG BUY – Ưu tiên hành động")
            for r in strong:
                st.markdown(f"### {r['Symbol']}")
                st.write(r["Recommendation"])
                st.write("👉", r["Reason"])
                st.plotly_chart(plot_chart(r["Data"], r["Symbol"]), use_container_width=True)

        else:
            st.info("Không có mã STRONG BUY hiện tại")

else:
    st.info("Nhập danh sách mã và bấm **SCAN NOW**")

# ======================
# FOOTER
# ======================
st.caption(f"Updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
