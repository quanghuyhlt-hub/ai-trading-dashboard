from vnstock import stock_historical_data
import pandas as pd
import pandas_ta as ta
from tqdm import tqdm
import time

# =============================
# CONFIG
# =============================
START_DATE = "2023-01-01"
END_DATE   = "2025-01-20"
VOLUME_MULTIPLIER = 1.5
SLEEP_TIME = 0.3   # tránh bị block

# =============================
# UNIVERSE (có thể đổi)
# =============================
STOCK_LIST = [
    "VCB","BID","CTG","ACB","TCB","MBB",
    "HPG","VNM","VIC","VHM","MSN",
    "SSI","VND","HCM",
    "GAS","PLX","POW",
    "FPT","MWG","PNJ"
]

# =============================
# HELPER FUNCTIONS
# =============================
def fetch_and_clean(symbol):
    try:
        df = stock_historical_data(
            symbol=symbol,
            start_date=START_DATE,
            end_date=END_DATE,
            resolution="1D"
        )
    except:
        return None, "API_ERROR"

    if df is None or len(df) < 200:
        return None, "NOT_ENOUGH_DATA"

    df = df.rename(columns={
        "TradingDate": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    if df["close"].isna().any():
        return None, "NULL_CLOSE"

    if (df["volume"] <= 0).any():
        return None, "BAD_VOLUME"

    return df, "OK"


def apply_indicators(df):
    df["MA20"] = ta.sma(df["close"], length=20)
    df["MA50"] = ta.sma(df["close"], length=50)
    df["MA200"] = ta.sma(df["close"], length=200)
    df["RSI"] = ta.rsi(df["close"], length=14)
    df["VOL_MA20"] = ta.sma(df["volume"], length=20)
    return df


def check_conditions(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    ma_cross = prev["MA20"] < prev["MA50"] and last["MA20"] > last["MA50"]
    price_above_ma200 = last["close"] > last["MA200"]
    rsi_ok = last["RSI"] > 50
    volume_breakout = last["volume"] > VOLUME_MULTIPLIER * last["VOL_MA20"]

    return ma_cross and price_above_ma200 and rsi_ok and volume_breakout


# =============================
# MAIN SCANNER
# =============================
results = []

for symbol in tqdm(STOCK_LIST):
    df, status = fetch_and_clean(symbol)

    if status != "OK":
        continue

    df = apply_indicators(df)

    try:
        if check_conditions(df):
            results.append({
                "symbol": symbol,
                "close": round(df["close"].iloc[-1], 2),
                "MA20": round(df["MA20"].iloc[-1], 2),
                "MA50": round(df["MA50"].iloc[-1], 2),
                "MA200": round(df["MA200"].iloc[-1], 2),
                "RSI": round(df["RSI"].iloc[-1], 2),
                "volume": int(df["volume"].iloc[-1])
            })
    except:
        pass

    time.sleep(SLEEP_TIME)

# =============================
# OUTPUT
# =============================
result_df = pd.DataFrame(results)

if not result_df.empty:
    result_df.to_csv("scanner_result.csv", index=False)
    print("🔥 DONE – Có kèo rồi sếp")
    print(result_df)
else:
    print("❌ Không có mã nào thỏa điều kiện")
