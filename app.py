import streamlit as st
import pandas as pd
import yfinance as yf
import ta

st.set_page_config(page_title="AI Stock Scanner", layout="wide")
st.title("🚀 AI Scan đa mã – Bảng hỗ trợ quyết định")

# ======================
# CONFIG
# ======================
DEFAULT_SYMBOLS = "VCB,CTG,BID,HPG,FPT,MWG,SSI"

# ======================
# INDICATORS
# ======================
def add_indicators(df):
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    df["MACD"] = ta.trend.MACD(df["Close"]).macd()
    return df

# ======================
# SCAN 1 MÃ
# ======================
def scan_symbol(symbol, period):
    try:
        df = yf.download(symbol, period=period, progress=False)
        if df.empty or len(df) < 60:
            return None

        df = add_indicators(df)
        last = df.iloc[-1]

        result = {
            "Mã": symbol,
            "MA20 > MA50": last["MA20"] > last["MA50"],
            "Giá > MA20": last["Close"] > last["MA20"],
            "RSI > 50": last["RSI"] > 50,
            "MACD > 0": last["MACD"] > 0,
        }

        result["Điểm"] = sum(result.values()) - 1  # trừ cột "Mã"
        return result

    except:
        return None

# ======================
# SIDEBAR
# ======================
symbols_input = st.sidebar.text_area(
    "Danh sách mã (phân cách bằng dấu ,)",
    DEFAULT_SYMBOLS
)
period = st.sidebar.selectbox("Khung dữ liệu", ["6mo", "1y", "2y"])

scan_btn = st.sidebar.button("🚀 Scan")

# ======================
# SCAN
# ======================
if scan_btn:
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    results = []

    with st.spinner("Đang scan thị trường..."):
        for sym in symbols:
            r = scan_symbol(sym, period)
            if r:
                results.append(r)

    if not results:
        st.error("❌ Không có dữ liệu hợp lệ")
        st.stop()

    df_result = pd.DataFrame(results)

    # sort theo điểm
    df_result = df_result.sort_values("Điểm", ascending=False)

    # convert bool -> icon
    for col in ["MA20 > MA50", "Giá > MA20", "RSI > 50", "MACD > 0"]:
        df_result[col] = df_result[col].apply(lambda x: "✅" if x else "❌")

    st.subheader("📊 BẢNG SCAN QUYẾT ĐỊNH")
    st.dataframe(df_result, use_container_width=True)

    # ======================
    # NHẬN ĐỊNH TỔNG
    # ======================
    st.subheader("📌 Nhận định nhanh")

    top = df_result.iloc[0]

    if top["Điểm"] >= 3:
        st.success(
            f"✅ **{top['Mã']}** đang là mã mạnh nhất trong danh sách – đáng ưu tiên theo dõi / vào lệnh"
        )
    else:
        st.warning("⚠️ Chưa có mã nào thật sự vượt trội – nên kiên nhẫn")
