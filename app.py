import streamlit as st
from vnstock import *
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="VN Stock Screener Pro", layout="wide")
st.title("🔥 VN Stock Screener Pro - Cá Nhân")

# Sidebar
if st.sidebar.button("🔄 Quét lại ngay"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.info(f"Cập nhật lúc: {datetime.datetime.now().strftime('%H:%M %d/%m/%Y')}")

@st.cache_data(ttl=300)  # Cache 5 phút
def scan_stocks():
    # Lấy tất cả mã
    symbols_df = ticker_overview()
    results = []

    for _, row in symbols_df.iterrows():
        symbol = row['ticker']
        exchange = row['exchange']
        try:
            # Realtime quote (giá hiện tại hoặc closing nếu ngoài giờ)
            quote = stock_quote(symbol)
            if quote.empty:
                continue
            current_price = float(quote['price'].iloc[0])
            change_pct = quote['change_pct'].iloc[0]
            volume_today = int(quote['volume'].iloc[0])

            # Historical data
            end_date = datetime.date.today().strftime("%Y-%m-%d")
            df = stock_historical_data(symbol, "2025-07-01", end_date, "1D")
            if len(df) < 60:
                continue

            df['MA20'] = df['close'].rolling(20).mean()
            df['MA50'] = df['close'].rolling(50).mean()
            avg_vol_20 = df['volume'].rolling(20).mean().iloc[-2]  # Avg 20 phiên trước

            conditions = []

            # 1. MA20 crossover MA50 trong 3 phiên gần nhất (bao gồm hôm nay)
            crossover_session = -1
            for i in range(1, 4):  # Check 3 phiên gần nhất
                if len(df) >= i + 1:
                    if df['MA20'].iloc[-i] > df['MA50'].iloc[-i] and df['MA20'].iloc[-i-1] <= df['MA50'].iloc[-i-1]:
                        crossover_session = i
                        conditions.append(f"MA20 cắt lên MA50 (cách {i-1} phiên)" if i > 1 else "MA20 chuẩn bị/cắt lên MA50 hôm nay")
                        break

            # 2. Volume surge
            if volume_today > 1.2 * avg_vol_20:
                conditions.append("Volume tăng >20% vs TB20")

            # 3. Flatbase ~10%
            period = 40
            if len(df) >= period:
                recent_df = df[-period:]
                high = recent_df['high'].max()
                low = recent_df['low'].min()
                avg_price = recent_df['close'].mean()
                amplitude = (high - low) / avg_price * 100
                if amplitude <= 12 and current_price >= (high + low) / 2:
                    conditions.append(f"Flatbase biên độ {amplitude:.1f}%")

            if conditions:
                results.append({
                    "Mã": symbol,
                    "Sàn": exchange,
                    "Giá": f"{current_price:,}",
                    "% Change": f"{change_pct:+.2f}%",
                    "KL hôm nay": f"{volume_today:,}",
                    "% KL vs TB20": f"{(volume_today / avg_vol_20 - 1)*100:+.1f}%" if avg_vol_20 > 0 else "N/A",
                    "Điều kiện": "; ".join(conditions)
                })

        except Exception as e:
            continue  # Bỏ qua lỗi

    return pd.DataFrame(results)

df_results = scan_stocks()

if df_results.empty:
    st.info("Hiện tại chưa có cổ phiếu nào thỏa điều kiện mạnh.")
else:
    st.success(f"Tìm thấy {len(df_results)} cổ phiếu tiềm năng!")
    st.dataframe(df_results.sort_values("% KL vs TB20", ascending=False), use_container_width=True)

# Optional: Chart cho mã top 1
if not df_results.empty:
    top_symbol = df_results.iloc[0]['Mã']
    with st.expander(f"Chart mẫu cho {top_symbol}"):
        df_chart = stock_historical_data(top_symbol, "2025-07-01", datetime.date.today().strftime("%Y-%m-%d"), "1D")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_chart['time'], open=df_chart['open'], high=df_chart['high'], low=df_chart['low'], close=df_chart['close'], name='Price'))
        fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['close'].rolling(20).mean(), name='MA20', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['close'].rolling(50).mean(), name='MA50', line=dict(color='blue')))
        st.plotly_chart(fig, use_container_width=True)
