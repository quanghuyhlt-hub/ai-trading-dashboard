import pandas as pd
import numpy as np

# ===== INDICATORS =====
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_indicators(df):
    df = df.copy()

    df["MA20"] = df["close"].rolling(20).mean()
    df["MA50"] = df["close"].rolling(50).mean()
    df["MA200"] = df["close"].rolling(200).mean()

    df["RSI"] = RSI(df["close"], 14)
    df["VOL_MA20"] = df["volume"].rolling(20).mean()

    return df


# ===== MA CROSS WITH TOLERANCE =====
def ma20_cross_up_recent(df, lookback=5):
    """
    True nếu trong lookback phiên gần nhất
    có MA20 cắt lên MA50
    """
    ma20 = df["MA20"]
    ma50 = df["MA50"]

    cross = (ma20.shift(1) <= ma50.shift(1)) & (ma20 > ma50)
    return cross.tail(lookback).any()


# ===== MAIN SCANNER =====
def scan_stock(df):
    df = compute_indicators(df)

    latest = df.iloc[-1]

    # ---- TẦNG 1 ----
    cond_layer1 = (
        latest["close"] > latest["MA200"] and
        latest["RSI"] > 50 and
        latest["volume"] > latest["VOL_MA20"]
    )

    if not cond_layer1:
        return False

    # ---- TẦNG 2 ----
    cond_layer2 = ma20_cross_up_recent(df, lookback=5)

    return cond_layer2
