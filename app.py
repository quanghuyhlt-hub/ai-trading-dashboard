import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Pro Trader+ Scanner", layout="wide")
st.title("🚀 PRO TRADER+ SCANNER")
st.caption("Trend • Entry • SL • TP • Win-rate estimate")

# ================= INDICATORS =================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = abs(df["High"] - df["Close"].shift())
    low_close = abs(df["Low"] - df["Close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ================= CORE ANALYSIS =================
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 60:
            return None

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()
        df["RSI"] = rsi(df["Close"])
        df["ATR"] = atr(df)

        last = df.iloc[-1]

        close = float(last["Close"])
        ma20 = float(last["MA20"])
        ma50 = float(last["MA50"])
        rsi_val = float(last["RSI"])
        atr_val = float(last["ATR"])

        score = 0
        notes = []

        # Trend
        if ma20 > ma50:
            score += 2
            notes.append("Uptrend (MA20 > MA50)")

        # Price position
        if abs(close - ma20) / ma20 * 100 <= 3:
            score += 2
            notes.append("Giá quanh MA20")

        # RSI
        if 50 <= rsi_val <= 65:
            score += 2
            notes.append("RSI khỏe")

        # Momentum
        if close > df["Close"].iloc[-5]:
            score += 1
            notes.append("Momentum ngắn hạn tốt")

        # ================= ENTRY / SL / TP =================
        entry = close
        sl = round(entry - 1.5 * atr_val, 2)
        tp1 = round(entry + 1.5 * atr_val, 2)
        tp2 = round(entry + 3 * atr_val, 2)

        rr = round((tp1 - entry) / (entry - sl), 2)

        # ================= CLASSIFY =================
        if score >= 6 and rr >= 1.2:
            level = "🔥 PRO TRADER+"
            action = "Có thể vào lệnh"
            winrate = "60–70%"
        elif score >= 4:
            level = "🟢 TRADER"
            action = "Theo dõi, chờ breakout"
            winrate = "50–55%"
        else:
            level = "⚠️ NO TRADE"
            action = "Không nên giao dịch"
            winrate = "<45%"

        return {
            "Symbol": symbol,
            "Close": round(close, 2),
            "RSI": round(rsi_val, 1),
            "Score": score,
            "Level": level,
            "Winrate": winrate,
            "Entry": round(entry, 2),
            "SL": sl,
            "TP1": tp1,
            "TP2": tp2,
            "RR": rr,
            "Action": action,
            "Notes": ", ".join(notes),
            "Data": df
        }

    except:
        return None


# ================= CHART =================
def plot_chart(df, symbol, entry, sl, tp1, tp2):
    fig = go.Figure()

    fig.add_candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    )

    fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))

    fig.add_hline(y=entry, line_dash="dot", annotation_text="ENTRY")
    fig.add_hline(y=sl, line_dash="dash", annotation_text="SL")
    fig.add_hline(y=tp1, line_dash="dot", annotation_text="TP1")
    fig.add_hline(y=tp2, line_dash="dot", annotation_text="TP2")

    fig.update_layout(height=520, title=symbol, xaxis_rangeslider_visible=False)
    return fig


# ================= UI =================
st.sidebar.header("⚙️ Scanner")

symbols_input = st.sidebar.text_area(
    "Danh sách mã (demo)",
    "VCB.VN, FPT.VN, HPG.VN, VNM.VN"
)

scan = st.sidebar.button("🚀 AUTO SCAN PRO+")

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# ================= RUN =================
if scan:
    results = []

    with st.spinner("Quét thị trường..."):
        for s in symbols:
            r = analyze_stock(s)
            if r:
                results.append(r)

    if not results:
        st.error("Không có mã hợp lệ")
    else:
        table = pd.DataFrame(results).drop(columns=["Data"])
        st.subheader("📊 BẢNG TỔNG HỢP")
        st.dataframe(table, use_container_width=True)

        pro = [r for r in results if r["Level"] == "🔥 PRO TRADER+"]

        if pro:
            st.subheader("🔥 PRO TRADER+ – SETUP CHUẨN")
            for r in pro:
                st.markdown(f"## {r['Symbol']}")
                st.write(f"**Entry:** {r['Entry']} | **SL:** {r['SL']} | **TP1:** {r['TP1']} | **TP2:** {r['TP2']}")
                st.write(f"**RR:** {r['RR']} | **Winrate:** {r['Winrate']}")
                st.write("🧠", r["Notes"])
                st.plotly_chart(
                    plot_chart(r["Data"], r["Symbol"], r["Entry"], r["SL"], r["TP1"], r["TP2"]),
                    use_container_width=True
                )
        else:
            st.info("Chưa có setup PRO TRADER+ hôm nay")

else:
    st.info("Nhập mã → bấm AUTO SCAN PRO+")

st.caption(f"Updated {datetime.now().strftime('%d/%m/%Y %H:%M')}")
