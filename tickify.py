# tickify.py
import os, csv, numpy as np, pandas as pd, random

# ===== 可调参数 =====
DATA_IN  = "data/origin_daily.csv"
DATA_OUT = "data/orderbook_top_ticks.csv"
SPREAD   = 0.02      # 顶档买卖价差
TICK_SIZE = 0.01
LOT       = 10       # 数量粒度
TS_START_NS = 1_600_000_000_000_000_000  # 任意起点ns
RNG_SEED  = 42

random.seed(RNG_SEED); np.random.seed(RNG_SEED)

def round_tick(p): return round(round(p / TICK_SIZE) * TICK_SIZE, 2)

def ticks_per_day(volume):  # 基于成交量的粗略分配，避免过少或过多
    return max(200, min(int(volume/1000), 5000))

def brownian_bridge(n, start, end, low, high, vol=0.25):
    t = np.linspace(0, 1, n)
    bm = np.cumsum(np.random.normal(scale=vol/np.sqrt(n), size=n))
    bridge = start + (end - start)*t + (bm - t*bm[-1])
    return np.clip(bridge, low, high)

def normalize_cols(df):
    # 接受 AAPL.Open 之类列名，统一成 Open/High/Low/Close/Volume
    ren = {}
    for c in df.columns:
        lc = c.lower()
        if "open" in lc and "aapl" in lc or lc.endswith(".open"): ren[c]="Open"
        if lc == "open": ren[c]="Open"
        if "high" in lc: ren[c]="High"
        if "low"  in lc: ren[c]="Low"
        if "close"in lc: ren[c]="Close"
        if "volume" in lc or lc in ("vol","volumn"): ren[c]="Volume"
        if lc == "date": ren[c]="Date"
    df = df.rename(columns=ren)
    need = {"Date","Open","High","Low","Close","Volume"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {missing}")
    return df

def main():
    os.makedirs(os.path.dirname(DATA_OUT), exist_ok=True)

    df = pd.read_csv(DATA_IN)
    df = normalize_cols(df)

    with open(DATA_OUT, "w", newline="") as f:
        csv.writer(f).writerow(["ts_ns","side","price","qty"])

    ts_ns = TS_START_NS
    for _, r in df.iterrows():
        try:
            o,h,l,c,v = float(r["Open"]), float(r["High"]), float(r["Low"]), float(r["Close"]), float(r["Volume"])
        except:
            continue
        n = ticks_per_day(v)
        if n <= 0: continue

        # 生成中间价轨迹
        mid_path = brownian_bridge(n, o, c, l, h, vol=0.25)

        # 把总量大致分配到每个tick（加随机，量化到LOT）
        qtys = np.maximum(LOT, (v/max(n,1))*(0.5+np.random.rand(n))).astype(int)
        qtys = (qtys // LOT) * LOT

        with open(DATA_OUT, "a", newline="") as f:
            w = csv.writer(f)
            for i in range(n):
                # 时间推进（每个tick间隔 50–200 微秒）
                ts_ns += np.random.randint(50_000, 200_000)
                mid = round_tick(mid_path[i])
                bid = round_tick(mid - SPREAD/2)
                ask = round_tick(mid + SPREAD/2)
                q = int(qtys[i])

                # 一次写两行：顶档买 & 顶档卖
                w.writerow([ts_ns, "BUY",  bid, q])
                w.writerow([ts_ns, "SELL", ask, q])

    print(f"[tickify] wrote {DATA_OUT}")

if __name__ == "__main__":
    main()
