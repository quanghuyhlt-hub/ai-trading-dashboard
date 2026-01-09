import streamlit as st
import pandas as pd
import yfinance as yf
import ta

st.set_page_config(page_title="AI Stock Scanner", layout="wide")
st.title("📊 AI Scan cổ phiếu – Bảng hỗ trợ quyết định")

# ======================
# HÀM TÍNH INDICATOR
# ======================
def add_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    df["MACD"] = ta.trend.MACD(df["Close"]).macd()

    return df

# ======================
# HÀM SCAN & CHẤM ĐIỂM
# ======================
def scan_conditions(df):
    last = df.iloc[-1]

    conditions = [
        {
            "Điều kiện": "MA20 > MA50",
            "Đạt": last["MA20"] > last["MA50"],
            "Giải thích": "Xu hướng trung hạn"
        },
        {
            "Điều kiện": "Giá > MA20",
            "Đạt": last["Close"] > last["MA20"],
            "Giải thích": "Giá đang khỏe"
        },
        {
            "Điều kiện": "RSI > 50",
            "Đạt": last["RSI"] > 50,
            "Giải thích": "Động lượng tăng"
        },
        {
            "Điều kiện": "MACD > 0",
            "Đạt": last["MACD"] > 0,
            "Giải thích": "Xung lực xu hướng"
        }
    ]

    score = sum([1 for c in conditions if c["Đạt"]])
    return score, pd.DataFrame(conditions)

# ======================
# SIDEBAR
# ======================
symbol = st.sidebar.text_input("Nhập mã cổ phiếu", "VCB")
period = st.sidebar.selectbox("Khung dữ liệu", ["6mo", "1y", "2y"])

# ======================
# LOAD DATA
# ======================
df = yf.download(symbol, period=period)

if df.empty:
    st.error("❌ Không lấy được dữ liệu")
    st.stop()

df = add_indicators(df)

score, table = scan_conditions(df)

# ======================
# HIỂN THỊ
# ======================
st.subheader(f"🔎 Kết quả scan: {symbol}")
st.metric("Điểm kỹ thuật", f"{score}/4")

table["Đạt"] = table["Đạt"].apply(lambda x: "✅" if x else "❌")
st.dataframe(table, use_container_width=True)

# ======================
# KHUYẾN NGHỊ
# ======================
st.subheader("📌 Nhận định nhanh")

if score >= 3:
    st.success("✅ Xu hướng TỐT – Có thể xem xét mua/giữ")
elif score == 2:
    st.warning("⚠️ Trung tính – Chờ xác nhận thêm")
else:
    st.error("❌ Xu hướng YẾU – Hạn chế vào lệnh")

# ======================
# CHART
# ======================
st.subheader("📈 Biểu đồ giá & MA")
st.line_chart(df[["Close", "MA20", "MA50"]])
