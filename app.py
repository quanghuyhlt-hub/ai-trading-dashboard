# app.py — Level X Trading Dashboard (Step 4: Trade plan + Top5 export)
import io
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Level X – Trading Dashboard", layout="wide")
st.title("📊 Level X – Trading Dashboard (Entry + Trade Plan)")

# -------------------
# Utilities / Data
# -------------------
def fetch_price(symbol):
    df = yf.Ticker(symbol).history(period="1y", interval="1d")
    if df.empty:
        return df
    df = df.reset_index()
    df.columns = [c if isinstance(c, str) else str(c) for c in df.columns]
    return df

@st.cache_data
def load_data(symbol):
    df = fetch_price(symbol)
    if df.empty:
        return df
    df = df.copy()
    # Moving averages
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    # Volume MA
    df["VOL_MA20"] = df["Volume"].rolling(20).mean()
    # ATR(14)
    df["H-L"] = df["High"] - df["Low"]
    df["H-PC"] = (df["High"] - df["Close"].shift(1)).abs()
    df["L-PC"] = (df["Low"] - df["Close"].shift(1)).abs()
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR14"] = df["TR"].rolling(14).mean()
    return df.dropna()

# -------------------
# Core detection and scoring
# -------------------
def detect_cross_row(df, lookback=5):
    """Return the row (Series) where MA20 crossed MA50 within `lookback` most recent rows.
       If none, return None."""
    if len(df) < 60:
        return None
    tmp = df.copy().dropna()
    tmp["prev_MA20"] = tmp["MA20"].shift(1)
    tmp["prev_MA50"] = tmp["MA50"].shift(1)
    recent = tmp.tail(lookback)
    cross_mask = (recent["prev_MA20"] < recent["prev_MA50"]) & (recent["MA20"] > recent["MA50"])
    if not cross_mask.any():
        return None
    return recent[cross_mask].iloc[-1]  # last cross within lookback

def bars_since_cross(df, cross_row):
    """Return number of bars since cross (0 = cross is last bar)."""
    if cross_row is None:
        return None
    idx_cross = cross_row.name
    pos_cross = df.index.get_loc(idx_cross)
    return len(df) - pos_cross - 1

def slope(series, n=3):
    if len(series) < n:
        return 0.0
    return float(series.iloc[-1] - series.iloc[-n])

def ai_score_simple(df, cross_row):
    """Rule-based score 0-100 (same idea as earlier but compact)."""
    if cross_row is None:
        return 0
    last = df.iloc[-1]
    score = 0
    # timing
    bars = bars_since_cross(df, cross_row)
    if bars <= 3:
        score += 30
    elif bars <= 5:
        score += 20
    else:
        score += 10
    # price gap
    gap = (last["Close"] - cross_row["Close"]) / cross_row["Close"]
    if gap <= 0.05:
        score += 30
    elif gap <= 0.10:
        score += 20
    elif gap <= 0.15:
        score += 10
    # volume
    if last["Volume"] > 2 * last["VOL_MA20"]:
        score += 20
    elif last["Volume"] > 1.5 * last["VOL_MA20"]:
        score += 10
    # slope
    if slope(df["MA20"]) > 0 and slope(df["MA50"]) > 0:
        score += 10  # small change: keep balance
    elif slope(df["MA20"]) > 0:
        score += 5
    return int(min(score, 100))

# -------------------
# Trade plan builder (Buy zone, SL, Targets, Pullback)
# -------------------
def compute_trade_plan(df, cross_row, max_gap=0.15, atr_mult_sl=1.5):
    """
    Returns dict:
      cross_price, buy_zone_low, buy_zone_high, stop_loss, targets(list),
      pullback_flag (bool), notes
    """
    last = df.iloc[-1]
    cross_price = float(cross_row["Close"])
    last_price = float(last["Close"])
    atr = float(last["ATR14"]) if "ATR14" in df.columns and not pd.isna(last["ATR14"]) else None

    # Buy zone: between cross_price and cross_price*(1+max_gap)
    buy_low = cross_price
    buy_high = cross_price * (1 + max_gap)

    # Stop loss: prefer below cross price by ATR*mult, else percentage fallback
    if atr is not None and atr > 0:
        stop_loss = cross_price - atr * atr_mult_sl
    else:
        # fallback: 6% below cross
        stop_loss = cross_price * 0.94

    # Ensure stop is below cross and not above current price
    if stop_loss >= last_price:
        stop_loss = last_price - (atr * atr_mult_sl if atr else last_price * 0.03)

    # Minimum buffer: 1% below cross
    stop_loss = min(stop_loss, cross_price * 0.99)

    # Targets: use gap (last - cross) multiplied by Fibonacci-ish multipliers if gap>0 else percent steps
    gap = last_price - cross_price
    if gap > 0:
        t1 = cross_price + gap * 1.0
        t2 = cross_price + gap * 1.618
        t3 = cross_price + gap * 2.618
    else:
        t1 = cross_price * 1.05
        t2 = cross_price * 1.10
        t3 = cross_price * 1.20

    targets = [round(float(x), 2) for x in (t1, t2, t3)]

    # Pullback "đẹp" detection:
    # - current price within buy zone OR slightly above buy_high (<= buy_high*1.03)
    # - AND price > MA20
    # - AND volume >= VOL_MA20
    pullback_flag = False
    if (last_price <= buy_high * 1.03) and (last_price >= buy_low * 0.95):
        if last_price > last["MA20"] and last["Volume"] >= last["VOL_MA20"]:
            pullback_flag = True

    notes = []
    notes.append(f"Cross price: {cross_price:.2f}")
    notes.append(f"Last price: {last_price:.2f}")
    if atr is not None:
        notes.append(f"ATR14: {atr:.2f}")

    plan = {
        "cross_price": round(cross_price, 2),
        "buy_zone_low": round(buy_low, 2),
        "buy_zone_high": round(buy_high, 2),
        "stop_loss": round(max(stop_loss, 0.0), 2),
        "targets": targets,
        "pullback": pullback_flag,
        "notes": " | ".join(notes)
    }
    return plan

# -------------------
# UI & Tabs
# -------------------
tab1, tab2 = st.tabs(["🔍 Phân tích 1 mã", "🧠 AUTO SCAN + TOP5"])

# TAB 1: single stock + trade plan
with tab1:
    symbol = st.text_input("Nhập mã cổ phiếu (VD: VNM.VN, HPG.VN...)", "VNM.VN")
    max_gap_pct = st.slider("Max gap from cross (%) allowed for buy zone", 5, 30, 15)
    atr_mult_sl = st.slider("Stoploss = ATR *", 1.0, 3.0, 1.5)
    if symbol:
        df = load_data(symbol)
        if df.empty:
            st.error("Không tải được dữ liệu cho mã này.")
        else:
            cross_row = detect_cross_row(df, lookback=5)
            if cross_row is None:
                st.warning("Chưa có MA20 cắt MA50 gần đây.")
                st.dataframe(df.tail(10))
            else:
                last = df.iloc[-1]
                score = ai_score_simple(df, cross_row)
                plan = compute_trade_plan(df, cross_row, max_gap=max_gap_pct/100.0, atr_mult_sl=atr_mult_sl)

                col1, col2, col3 = st.columns([1,1,1])
                col1.metric("AI Score", score)
                col2.metric("Pullback đẹp", "YES" if plan["pullback"] else "NO")
                col3.metric("Days since cross", bars_since_cross(df, cross_row))

                st.markdown("**Trade plan**")
                st.write(plan["notes"])
                st.write(f"Buy zone: {plan['buy_zone_low']} → {plan['buy_zone_high']}")
                st.write(f"Stop loss (suggest): {plan['stop_loss']}")
                st.write("Targets: " + ", ".join([str(x) for x in plan["targets"]]))

                # Chart with annotations
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], name="MA20", line=dict(color="blue")))
                fig.add_trace(go.Scatter(x=df["Date"], y=df["MA50"], name="MA50", line=dict(color="red")))

                # shapes: buy zone rectangle and stop/targets lines
                buy_low = plan["buy_zone_low"]; buy_high = plan["buy_zone_high"]
                stop = plan["stop_loss"]
                t1, t2, t3 = plan["targets"]

                # shade buy zone on last 60 days x-axis
                try:
                    x0 = df["Date"].iloc[-60]
                except:
                    x0 = df["Date"].iloc[0]
                x1 = df["Date"].iloc[-1]

                fig.add_shape(type="rect", x0=x0, x1=x1, y0=buy_low, y1=buy_high, fillcolor="LightGreen", opacity=0.15, line_width=0)
                # lines
                fig.add_hline(y=stop, line=dict(color="orange", dash="dot"), annotation_text="Stop", annotation_position="bottom right")
                fig.add_hline(y=t1, line=dict(color="green", dash="dash"), annotation_text="T1", annotation_position="top right")
                fig.add_hline(y=t2, line=dict(color="green", dash="dash"), annotation_text="T2", annotation_position="top right")
                fig.add_hline(y=t3, line=dict(color="green", dash="dash"), annotation_text="T3", annotation_position="top right")

                fig.update_layout(height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

# TAB 2: Auto scan full list, compute AI score, trade plan, top5 export
with tab2:
    st.subheader("Auto Scan – nhập danh sách / quét full sàn")

    symbols_text = st.text_area("Danh sách mã (1 mã mỗi dòng). Dán full list HOSE+HNX nếu cần.",
                               value="VNM.VN\nHPG.VN\nFPT.VN\nMWG.VN\nVCB.VN\nSSI.VN")
    lookback = st.number_input("Lookback (phiên) để xét cross", min_value=1, max_value=10, value=5)
    max_gap_pct = st.slider("Max gap from cross (%) for buy zone (used for plan)", 5, 30, 15)
    atr_mult_sl = st.slider("ATR multiplier for SL", 1.0, 3.0, 1.5)
    min_score = st.slider("Min AI Score to include in Top list", 50, 100, 60)

    if st.button("🚀 SCAN FULL"):
        syms = [s.strip() for s in symbols_text.splitlines() if s.strip()]
        table = []
        plans = {}
        for sym in syms:
            try:
                df = load_data(sym)
            except Exception:
                continue
            if df.empty:
                continue
            cross = detect_cross_row(df, lookback=lookback)
            if cross is None:
                continue
            score = ai_score_simple(df, cross)
            if score < min_score:
                continue
            plan = compute_trade_plan(df, cross, max_gap=max_gap_pct/100.0, atr_mult_sl=atr_mult_sl)
            last = df.iloc[-1]
            pct_from_cross = round((last["Close"]/plan["cross_price"] - 1) * 100, 1)
            table.append({
                "Mã": sym,
                "Giá": round(last["Close"], 2),
                "AI Score": score,
                "% từ điểm cắt": pct_from_cross,
                "Pullback": "Yes" if plan["pullback"] else "No"
            })
            plans[sym] = plan

        if not table:
            st.warning("Không có mã nào đạt điều kiện.")
        else:
            df_table = pd.DataFrame(table).sort_values("AI Score", ascending=False).reset_index(drop=True)
            st.dataframe(df_table)

            # Top5
            top5 = df_table.head(5)
            st.markdown("### 🔝 Top 5")
            st.table(top5)

            # Download Top5 CSV
            csv_buf = io.StringIO()
            top5.to_csv(csv_buf, index=False)
            csv_bytes = csv_buf.getvalue().encode()
            st.download_button("⬇️ Tải Top5 CSV", data=csv_bytes, file_name="top5_scan.csv", mime="text/csv")

            # Show trade plan details for selected symbol from Top5
            st.markdown("### Chi tiết trade plan (Top5)")
            sel = st.selectbox("Chọn mã xem plan", options=list(plans.keys()), index=0)
            plan = plans[sel]
            st.write(plan)
            # show small chart for selected
            df_sel = load_data(sel)
            fig2 = go.Figure()
            fig2.add_trace(go.Candlestick(x=df_sel["Date"], open=df_sel["Open"], high=df_sel["High"], low=df_sel["Low"], close=df_sel["Close"], name="Price"))
            fig2.add_trace(go.Scatter(x=df_sel["Date"], y=df_sel["MA20"], name="MA20"))
            fig2.add_trace(go.Scatter(x=df_sel["Date"], y=df_sel["MA50"], name="MA50"))
            fig2.add_hline(y=plan["buy_zone_low"], line=dict(color="green", dash="dot"))
            fig2.add_hline(y=plan["buy_zone_high"], line=dict(color="green", dash="dot"))
            fig2.add_hline(y=plan["stop_loss"], line=dict(color="orange", dash="dash"))
            for t in plan["targets"]:
                fig2.add_hline(y=t, line=dict(color="blue", dash="dash"))
            fig2.update_layout(height=450, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig2, use_container_width=True)
