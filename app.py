# app.py
# Level X – Auto Scan (Phân tầng + Khuyến nghị tiếng Việt)
# Copy nguyên file này vào app.py, save và chạy: `streamlit run app.py`

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Level X – Stock Decision Scanner", layout="wide")
st.title("📊 Level X – Bộ lọc và khuyến nghị (MA20 / MA50 + Momentum)")

# -----------------------------
# CÁC HÀM TIỆN ÍCH
# -----------------------------
@st.cache_data(ttl=3600)
def load_data(symbol: str, period: str = "1y"):
    """
    Lấy dữ liệu giá từ yfinance, xử lý MultiIndex nếu có.
    Trả về DataFrame chuẩn hoặc None.
    """
    try:
        df = yf.download(symbol, period=period, interval="1d", progress=False)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    # Fix MultiIndex columns returned sometimes
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df = df.loc[:, ["Date", "Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    if len(df) < 60:
        return None
    return df


def sma(series: pd.Series, window: int):
    return series.rolling(window).mean()


def calc_rsi(series: pd.Series, period: int = 14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(series: pd.Series, fast=12, slow=26):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


def calc_atr(df: pd.DataFrame, n: int = 14):
    h_l = df["High"] - df["Low"]
    h_pc = (df["High"] - df["Close"].shift(1)).abs()
    l_pc = (df["Low"] - df["Close"].shift(1)).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def add_indicators(df: pd.DataFrame):
    """Thêm MA20, MA50, RSI, MACD, VolMA20, ATR14 vào df (trả về df copy)"""
    df = df.copy()
    df["MA20"] = sma(df["Close"], 20)
    df["MA50"] = sma(df["Close"], 50)
    df["RSI"] = calc_rsi(df["Close"], 14)
    df["MACD"] = calc_macd(df["Close"])
    df["Vol_MA20"] = sma(df["Volume"], 20)
    df["ATR14"] = calc_atr(df, 14)
    df.dropna(inplace=True)
    return df


def find_last_cross_index(df: pd.DataFrame):
    """
    Tìm index (label) của lần MA20 cắt MA50 gần nhất (MA20 lên trên MA50).
    Trả về index (label) hoặc None.
    """
    cross_mask = (df["MA20"] > df["MA50"]) & (df["MA20"].shift(1) <= df["MA50"].shift(1))
    if cross_mask.any():
        return df.index[cross_mask][-1]
    return None


def compute_signals(df: pd.DataFrame, params: dict):
    """
    Trả về:
      score (0-100),
      details (dict),
      recommendation (string, tiếng Việt),
      action (dict: buy_zone, stop_loss, targets)
    """
    details = {}
    # ensure indicators exist
    if df is None or df.empty or len(df) < 60:
        return None, None, None, None

    df = df.copy()
    last = df.iloc[-1]

    # last cross
    cross_idx = find_last_cross_index(df)
    if cross_idx is not None:
        days_from_cross = len(df) - df.index.get_loc(cross_idx) - 1
        cross_price = float(df.loc[cross_idx, "Close"])
    else:
        days_from_cross = None
        cross_price = None

    # numeric metrics
    dist_to_ma20 = float((last["Close"] - last["MA20"]) / last["MA20"] * 100)
    vol_today = float(last["Volume"])
    vol_ma20 = float(df["Vol_MA20"].iloc[-1]) if "Vol_MA20" in df.columns else np.nan
    avg_vol20 = vol_ma20
    rsi = float(last["RSI"]) if "RSI" in df.columns else np.nan
    macd = float(last["MACD"]) if "MACD" in df.columns else np.nan
    atr14 = float(last["ATR14"]) if "ATR14" in df.columns else np.nan

    # flags
    f_trend = last["MA20"] > last["MA50"]
    f_recent_cross = (days_from_cross is not None) and (days_from_cross <= params["max_days_since_cross"])
    f_price_ok = dist_to_ma20 <= params["max_dist_pct"]
    f_vol_ok = (not np.isnan(vol_ma20)) and (vol_today >= params["vol_mult"] * vol_ma20)
    f_liquidity = (not np.isnan(avg_vol20)) and (avg_vol20 >= params["min_avg_vol"])
    f_rsi = (not np.isnan(rsi)) and (params["rsi_low"] <= rsi <= params["rsi_high"])
    f_macd = (not np.isnan(macd)) and (macd > 0)

    # weights
    weights = {
        "trend": 20,
        "recent_cross": 25,
        "price_dist": 15,
        "volume": 15,
        "liquidity": 5,
        "rsi": 10,
        "macd": 10
    }

    score = 0
    score += weights["trend"] if f_trend else 0
    score += weights["recent_cross"] if f_recent_cross else 0
    score += weights["price_dist"] if f_price_ok else 0
    score += weights["volume"] if f_vol_ok else 0
    score += weights["liquidity"] if f_liquidity else 0
    score += weights["rsi"] if f_rsi else 0
    score += weights["macd"] if f_macd else 0
    score = max(0, min(100, int(score)))

    # recommendation mapping
    if score >= 85:
        rec = "🔥 NÊN THEO DÕI SÁT – CANH MUA"
    elif score >= 70:
        rec = "🟡 CÓ THỂ CANH (THEO DÕI)"
    elif score >= 50:
        rec = "⚠️ QUAN SÁT"
    else:
        rec = "🔴 CHƯA ƯU TIÊN"

    # action plan (if have cross)
    action = {}
    last_price = float(last["Close"])
    if cross_price is not None:
        buy_low = cross_price
        buy_high = cross_price * (1 + params["max_dist_pct"] / 100.0)
        # stop loss with ATR
        if not np.isnan(atr14) and atr14 > 0:
            stop_loss = cross_price - atr14 * params["atr_mult_sl"]
        else:
            stop_loss = cross_price * 0.94
        if stop_loss >= last_price:
            stop_loss = last_price * 0.98
        # targets
        gap = last_price - cross_price
        if gap > 0:
            t1 = cross_price + gap * 1.0
            t2 = cross_price + gap * 1.618
            t3 = cross_price + gap * 2.618
        else:
            t1 = cross_price * 1.05
            t2 = cross_price * 1.10
            t3 = cross_price * 1.20

        action = {
            "cross_price": round(cross_price, 2),
            "buy_zone": (round(buy_low, 2), round(buy_high, 2)),
            "stop_loss": round(float(stop_loss), 2),
            "targets": [round(t1, 2), round(t2, 2), round(t3, 2)],
            "atr14": round(float(atr14), 2) if not np.isnan(atr14) else None
        }
    else:
        action = {"note": "Chưa có điểm cắt MA20->MA50 trong dữ liệu"}

    details = {
        "trend": f_trend,
        "recent_cross": f_recent_cross,
        "days_from_cross": days_from_cross if days_from_cross is not None else -1,
        "dist_to_ma20_pct": round(dist_to_ma20, 2),
        "vol_today": int(vol_today),
        "vol_ma20": int(vol_ma20) if not np.isnan(vol_ma20) else None,
        "vol_ok": f_vol_ok,
        "liquidity_ok": f_liquidity,
        "rsi": round(rsi, 1) if not np.isnan(rsi) else None,
        "macd": round(macd, 3) if not np.isnan(macd) else None
    }

    return score, details, rec, action


# -----------------------------
# SIDEBAR: tham số do user chỉnh
# -----------------------------
st.sidebar.header("Cấu hình bộ lọc")
period = st.sidebar.selectbox("Khoảng thời gian lấy dữ liệu", ["6mo", "1y", "2y"], index=0)
symbols_text = st.sidebar.text_area(
    "Danh sách mã (mỗi dòng 1 mã). Ví dụ: HPG.VN",
    value="HPG.VN\nFPT.VN\nMWG.VN\nVNM.VN\nSSI.VN\nVND.VN\nPOW.VN\nPNJ.VN",
    height=180
)

max_days_since_cross = st.sidebar.slider("Số phiên kể từ cross (N)", 1, 20, 5)
vol_mult = st.sidebar.slider("Volume multiplier so với VolMA20", 1.0, 3.0, 1.5)
max_dist_pct = st.sidebar.slider("Giá cách MA20 tối đa (%)", 1, 30, 12)
min_avg_vol = st.sidebar.number_input("Min avg volume 20 ngày (số cổ)", value=0, min_value=0)
atr_mult_sl = st.sidebar.slider("ATR multiplier cho stoploss", 1.0, 3.0, 1.5)
rsi_low = st.sidebar.slider("RSI thấp (min)", 30, 50, 45)
rsi_high = st.sidebar.slider("RSI cao (max)", 60, 85, 70)

params = {
    "max_days_since_cross": max_days_since_cross,
    "vol_mult": vol_mult,
    "max_dist_pct": max_dist_pct,
    "min_avg_vol": min_avg_vol,
    "atr_mult_sl": atr_mult_sl,
    "rsi_low": rsi_low,
    "rsi_high": rsi_high
}

st.sidebar.markdown("---")
st.sidebar.markdown("Nhấn **Scan** để quét các mã trong danh sách.")

# -----------------------------
# MAIN UI
# -----------------------------
st.markdown("### 🔎 Auto Scan & Phân tầng tín hiệu (Level X)")
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🚀 Scan bây giờ"):
        do_scan = True
    else:
        do_scan = False

symbols = [s.strip().upper() for s in symbols_text.splitlines() if s.strip()]

# Containers for UI sections
top_container = st.container()
watch_container = st.container()
other_container = st.container()

if do_scan:
    if not symbols:
        st.warning("Chưa có mã nào để quét. Dán danh sách mã vào sidebar.")
    else:
        with st.spinner("Đang quét... (mỗi mã ~0.5s -> vài chục mã vài chục giây)"):
            rows = []
            plans = {}
            for sym in symbols:
                df = load_data(sym, period)
                if df is None:
                    continue
                df = add_indicators(df)
                score, details, rec, action = compute_signals(df, params)
                if score is None:
                    continue
                row = {
                    "Mã": sym,
                    "Giá": round(df["Close"].iloc[-1], 2),
                    "Score": score,
                    "Nhận định": rec,
                    # chi tiết để hiển thị cột
                    "Phiên từ Cross": details["days_from_cross"],
                    "Cách MA20 (%)": details["dist_to_ma20_pct"],
                    "RSI": details["rsi"],
                    "VolToday": details["vol_today"],
                    "VolMA20": details["vol_ma20"],
                    "VolOk": "✅" if details["vol_ok"] else "❌",
                    "Trend": "✅" if details["trend"] else "❌"
                }
                rows.append(row)
                plans[sym] = {"details": details, "action": action, "score": score, "rec": rec}

            if not rows:
                st.warning("Không có mã hợp lệ / đủ dữ liệu.")
            else:
                df_all = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

                # PHÂN TẦNG: lấy top group
                top_picks = df_all[df_all["Score"] >= 85].head(10)
                watch_picks = df_all[(df_all["Score"] >= 70) & (df_all["Score"] < 85)]
                other_picks = df_all[df_all["Score"] < 70]

                # Top section (cards)
                with top_container:
                    st.markdown("## 🟢 MÃ ƯU TIÊN (Top picks)")
                    if not top_picks.empty:
                        cols = st.columns(min(3, len(top_picks)))
                        for i, (_, r) in enumerate(top_picks.iterrows()):
                            c = cols[i % len(cols)]
                            sym = r["Mã"]
                            c.metric(label=f"{sym} — Score {r['Score']}", value=r["Giá"])
                            c.write(f"**Nhận định:** {r['Nhận định']}")
                            det = plans[sym]["details"]
                            act = plans[sym]["action"]
                            c.write(f"• Phiên từ Cross: {det['days_from_cross']}")
                            c.write(f"• Cách MA20: {det['dist_to_ma20_pct']}% | RSI: {det['rsi']}")
                            if "buy_zone" in act:
                                c.write(f"• Buy zone: {act['buy_zone'][0]} → {act['buy_zone'][1]}")
                                c.write(f"• Stop loss (gợi ý): {act['stop_loss']}")
                                c.write(f"• Targets: {act['targets']}")
                    else:
                        st.info("Không có mã nào ở mức ưu tiên cao (Score ≥ 85).")

                # Watchlist section
                with watch_container:
                    st.markdown("## 🟡 Danh sách theo dõi (Watchlist)")
                    if not watch_picks.empty:
                        st.dataframe(watch_picks.drop(columns=["Trend", "VolOk"]).reset_index(drop=True), use_container_width=True)
                    else:
                        st.info("Không có mã nào ở mức quan sát (70–84).")

                # Others (collapsed)
                with other_container:
                    st.markdown("## 🔴 Các mã khác (không ưu tiên)")
                    if not other_picks.empty:
                        with st.expander(f"Hiển thị {len(other_picks)} mã không ưu tiên"):
                            st.dataframe(other_picks.reset_index(drop=True), use_container_width=True)
                    else:
                        st.info("Không có mã ở nhóm này.")

                # Export Top picks CSV
                if not top_picks.empty:
                    csv = top_picks.to_csv(index=False).encode()
                    st.download_button("⬇️ Tải Top picks (CSV)", data=csv, file_name=f"top_picks_{datetime.now().date()}.csv")

                # Select a symbol to see detailed plan
                st.markdown("### 🔍 Xem chi tiết trade plan cho 1 mã")
                sel_sym = st.selectbox("Chọn mã", options=list(plans.keys()))
                if sel_sym:
                    sel = plans[sel_sym]
                    st.subheader(f"Chi tiết: {sel_sym} — Score {sel['score']} — {sel['rec']}")
                    st.write("Details:", sel["details"])
                    st.write("Action plan:", sel["action"])
                    # show small chart
                    df_sel = load_data(sel_sym, period)
                    df_sel = add_indicators(df_sel)
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df_sel["Date"], open=df_sel["Open"], high=df_sel["High"], low=df_sel["Low"], close=df_sel["Close"], name="Price"))
                    fig.add_trace(go.Scatter(x=df_sel["Date"], y=df_sel["MA20"], name="MA20"))
                    fig.add_trace(go.Scatter(x=df_sel["Date"], y=df_sel["MA50"], name="MA50"))
                    if "action" in sel and sel["action"].get("buy_zone"):
                        b0, b1 = sel["action"]["buy_zone"]
                        fig.add_hline(y=b0, line=dict(color="green", dash="dash"), annotation_text="Buy Low", annotation_position="bottom right")
                        fig.add_hline(y=b1, line=dict(color="green", dash="dash"), annotation_text="Buy High", annotation_position="top right")
                    if "action" in sel and sel["action"].get("stop_loss"):
                        fig.add_hline(y=sel["action"]["stop_loss"], line=dict(color="red", dash="dot"), annotation_text="Stop Loss", annotation_position="bottom right")
                    for t in sel["action"].get("targets", []):
                        fig.add_hline(y=t, line=dict(color="blue", dash="dash"))
                    fig.update_layout(height=450, xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
