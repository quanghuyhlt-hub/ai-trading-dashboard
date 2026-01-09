import streamlit as st
import pandas as pd
import yfinance as yf

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="Level X – Trading Dashboard",
    layout="wide"
)

st.title("📊 Level X – Trading Dashboard")

# ======================
# DATA
# ======================
def fetch_price(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y", interval="1d")
    if df.empty:
        return df
    df = df.reset_index()
    return df


@st.cache_data
def load_data(symbol):
    df = fetch_price(symbol)
    if df.empty:
        return df

    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()

    return df


# ======================
# LOGIC
# ======================
def detect_ma20_cross(df, lookback=5):
    df = df.dropna().copy()
    if len(df) < 60:
        return None

    df["prev_MA20"] = df["MA20"].shift(1)
    df["prev_MA50"] = df["MA50"].shift(1)

    recent = df.tail(lookback)

    cross_rows = recent[
        (recent["prev_MA20"] < recent["prev_MA50"]) &
        (recent["MA20"] > recent["MA50"])
    ]

    if cross_rows.empty:
        return None

    return cross_rows.iloc[-1]


def price_not_too_far(df, cross_row, max_gap=0.15):
    last_price = df.iloc[-1]["Close"]
    cross_price = cross_row["Close"]
    return (last_price - cross_price) / cross_price <= max_gap


def volume_breakout(df, multiplier=1.5):
    last = df.iloc[-1]
    return last["Volume"] > multiplier * last["VOL_MA20"]


# ======================
# TABS
# ======================
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN"])

# ======================
# TAB 1
# ======================
with tab1:
    symbol = st.text_input(
        "Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN, FPT.VN)",
        value="VNM.VN"
    )

    if symbol:
        df = load_data(symbol)

        if df.empty:
            st.error("❌ Không có dữ liệu")
        else:
            cross = detect_ma20_cross(df)

            last = df.iloc[-1]
            st.metric("Giá hiện tại", round(last["Close"], 2))

            if cross is None:
                st.warning("⏳ Chưa có MA20 cắt MA50 gần đây")
            else:
                ok_price = price_not_too_far(df, cross)
                ok_vol = volume_breakout(df)

                st.success("🔥 MA20 vừa cắt MA50")
                st.write(f"📌 Giá tại điểm cắt: **{round(cross['Close'],2)}**")

                if ok_price:
                    st.success("✅ Giá chưa chạy quá xa")
                else:
                    st.error("❌ Giá đã chạy quá +15%")

                if ok_vol:
                    st.success("✅ Volume bùng nổ")
                else:
                    st.warning("⚠️ Volume chưa đủ mạnh")

            st.dataframe(df.tail(10))


# ======================
# TAB 2 – AUTO SCAN
# ======================
with tab2:
    st.subheader("🧠 Auto Scan – Entry sớm")

    symbols = st.text_area(
        "Danh sách mã (mỗi mã 1 dòng)",
        value="VNM.VN\nHPG.VN\nFPT.VN\nVCB.VN\nMWG.VN"
    )

    lookback = st.slider("Số phiên MA20 cắt MA50", 1, 10, 5)
    max_gap = st.slider("Giá tối đa vượt điểm cắt (%)", 5, 30, 15) / 100
    vol_multi = st.slider("Volume so với MA20", 1.0, 3.0, 1.5)

    if st.button("🚀 SCAN"):
        results = []

        for sym in symbols.splitlines():
            sym = sym.strip()
            if not sym:
                continue

            df = load_data(sym)
            if df.empty:
                continue

            cross = detect_ma20_cross(df, lookback)
            if cross is None:
                continue

            if not price_not_too_far(df, cross, max_gap):
                continue

            if not volume_breakout(df, vol_multi):
                continue

            last = df.iloc[-1]

            results.append({
                "Mã": sym,
                "Giá hiện tại": round(last["Close"], 2),
                "Giá lúc cắt": round(cross["Close"], 2),
                "% tăng": round((last["Close"]/cross["Close"] - 1) * 100, 1),
                "Volume": int(last["Volume"])
            })

        if results:
            st.success(f"✅ {len(results)} mã entry đẹp")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("❌ Không có mã nào đạt chuẩn")
