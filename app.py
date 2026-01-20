import streamlit as st
import pandas as pd
import numpy as np
import time

# ======================
# CONFIG
# ======================
st.set_page_config(
    page_title="Stock Scanner",
    layout="wide"
)

st.title("📊 Simple Stock Scanner (CSV Only)")
st.caption("No API • No Yahoo • No vnstock • CSV-driven")

# ======================
# LOAD SYMBOL LIST
# ======================
@st.cache_data
def load_symbols():
    df = pd.read_csv("stocks.csv")
    df = df.dropna()
    df["symbol"] = df["symbol"].astype(str).str.upper()
    return df

symbols_df = load_symbols()
symbols = symbols_df["symbol"].tolist()

st.success(f"Loaded {len(symbols)} symbols")

# ======================
# SCAN LOGIC (MOCK – FAST – STABLE)
# ======================
def scan_symbols(symbols):
    results = []

    for sym in symbols:
        # giả lập dữ liệu scan (thay bằng logic thật sau)
        price = round(np.random.uniform(10, 120), 2)
        volume = np.random.randint(100_000, 5_000_000)
        score = round(np.random.uniform(0, 100), 1)

        # điều kiện scan (đúng yêu cầu: CÓ ĐIỀU KIỆN)
        breakout = price > 50 and volume > 1_000_000
        strong = score >= 70

        if breakout and strong:
            results.append({
                "Symbol": sym,
                "Price": price,
                "Volume": volume,
                "Score": score,
                "Signal": "🔥 STRONG"
            })

    return pd.DataFrame(results)

# ======================
# UI CONTROL
# ======================
col1, col2 = st.columns([1, 3])

with col1:
    run_scan = st.button("🚀 Run Scan")

with col2:
    st.info("Scan chạy local trên CSV – cực nhanh, không phụ thuộc bên ngoài")

# ======================
# RUN SCAN
# ======================
if run_scan:
    start = time.time()
    with st.spinner("Scanning..."):
        result_df = scan_symbols(symbols)
    end = time.time()

    st.success(f"Done in {round(end - start, 2)}s")

    if result_df.empty:
        st.warning("No stocks matched conditions")
    else:
        st.subheader("📌 Scan Results")
        st.dataframe(
            result_df.sort_values("Score", ascending=False),
            use_container_width=True
        )

# ======================
# RAW DATA VIEW
# ======================
with st.expander("📄 View raw symbol list"):
    st.dataframe(symbols_df, use_container_width=True)
