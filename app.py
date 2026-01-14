import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Pro Trader – Break Scanner", layout="wide")
st.title("🚀 PRO TRADER – LEVEL 2: BREAK NỀN / SIÊU CỔ")

# ================= LOAD SYMBOLS =================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")  # chỉ cần cột symbol
    return df["symbol"].dropna().unique().tolist()

# ================= LOAD PRICE =================
@st.cache_data
def load_price(symbol):
    df = yf.download(symbol + ".VN", period="9mo", interval="1d", progress=False)
    if df.empty or len(df) < 80:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================= FIND MA CROSS =================
def find_ma_cross_price(df):
    for i in range(len(df) - 1, 20, -1):
        if (
            df["MA20"].iloc[i] > df["MA50"].iloc[i]
            and df["MA20"].iloc[i - 1] <= df["MA50"].iloc[i - 1]
        ):
            return df["Close"].iloc[i]
    return None

# ================= ANALYZE BREAK =================
def analyze_break(df):
    last = df.iloc[-1]
    cross_price = find_ma_cross_price(df)

    if cross_price is None:
        return None

    increase_pct = (last["Close"] - cross_price) / cross_price * 100
    dist_ma20 = (last["Close"] - last["MA20"]) / last["MA20"] * 100

    conditions = []
    score = 0

    if last["Close"] > last["MA20"]:
        score += 1
        conditions.append("Giá trên MA20")

    if last["MA20"] > last["MA50"]:
        score += 1
        conditions.append("Trend tăng")

    if increase_pct < 10:
        score += 2
        conditions.append("Chưa tăng nóng")

    if abs(dist_ma20) < 5:
        score += 1
        conditions.append("Đang nén giá")

    if last["Volume"] > last["VOL_MA20"]:
        score += 1
        conditions.append("Volume vào")

    if 50 <= last["RSI"] <= 68:
        score += 1
        conditions.append("RSI khỏe")

    if score >= 7:
        reco = "MUA SỚM – BREAK NỀN"
    elif score >= 5:
        reco = "THEO DÕI – CHỜ BREAK"
    else:
        reco = "LOẠI"

    return {
        "Giá": round(last["Close"], 2),
        "RSI": round(last["RSI"], 1),
        "% tăng từ MA cắt": round(increase_pct, 1),
        "Điểm": score,
        "Khuyến nghị": reco,
        "Lý do": "; ".join(conditions)
    }

# ================= MAIN =================
symbols = load_symbols()
results = []

st.info(f"🔍 Đang quét {len(symbols)} mã cổ phiếu (Level 2)...")

for sym in symbols:
    df = load_price(sym)
    if df is None:
        continue

    data = analyze_break(df)
    if data and data["Khuyến nghị"] != "LOẠI":
        data["Mã"] = sym
        results.append(data)

# ================= OUTPUT =================
if results:
    df_out = pd.DataFrame(results).sort_values("Điểm", ascending=False)
    st.dataframe(df_out, use_container_width=True)
else:
    st.warning("Không có mã nào đạt chuẩn BREAK NỀN hôm nay.")
