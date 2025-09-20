import pandas as pd
import matplotlib.pyplot as plt
import yaml
import os

# === 1. 读取配置文件，拿手续费 ===
with open("../configs/run.yaml", "r") as f:
    cfg = yaml.safe_load(f)

maker_fee_bps = cfg["fees_bps"]["maker"]
taker_fee_bps = cfg["fees_bps"]["taker"]

print(f"Loaded fees: maker={maker_fee_bps} bps, taker={taker_fee_bps} bps")

# === 2. 读取成交日志 ===
trade_file = "../trades.csv"
if not os.path.exists(trade_file):
    print("No trades.csv found. Please run the C++ engine first.")
    exit()

df = pd.read_csv(trade_file)
print("=== Trades Loaded ===")
print(df.head())

# === 3. 相对时间（毫秒） ===
t0 = df["ts_ns"].iloc[0]
df["ts_rel_ms"] = (df["ts_ns"] - t0) / 1e6   # 转换成毫秒

# === 4. 计算 PnL，考虑手续费 ===
df["buy_cashflow"] = -df["price"] * df["qty"] * (1 + taker_fee_bps / 10000.0)
df["sell_cashflow"] = df["price"] * df["qty"] * (1 - maker_fee_bps / 10000.0)

# 假设跟踪 BUY#1
pnl = df.loc[df["buy_id"] == 1, "buy_cashflow"].cumsum()

# === 5. 画图 ===
plt.figure(figsize=(9,4))
plt.plot(df.loc[df["buy_id"] == 1, "ts_rel_ms"], pnl.values,
         marker="o", label="PnL for BUY#1 (with fees)")
plt.axhline(0, color="black", linestyle="--", linewidth=1)
plt.title("Cumulative PnL for BUY#1 (Relative Time)")
plt.xlabel("Time since first trade (ms)")
plt.ylabel("PnL")
plt.legend()
plt.tight_layout()

os.makedirs("out", exist_ok=True)
out_path = "out/pnl_curve_relative_time.png"
plt.savefig(out_path)
print(f"\nPnL curve saved to {out_path}")
