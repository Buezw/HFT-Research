import pandas as pd
import matplotlib.pyplot as plt
import yaml
import os

# === 1. 读取配置文件，拿到手续费 ===
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

# === 3. 模拟 PnL，考虑手续费 ===
# 假设：买方 = taker（吃单），卖方 = maker（挂单）
df["buy_cashflow"] = -df["price"] * df["qty"] * (1 + taker_fee_bps / 10000.0)
df["sell_cashflow"] = df["price"] * df["qty"] * (1 - maker_fee_bps / 10000.0)

# 跟踪 BUY#1 的累计 PnL
pnl = df.loc[df["buy_id"] == 1, "buy_cashflow"].cumsum()

# === 4. 画图 ===
plt.figure(figsize=(8,4))
plt.plot(pnl.index, pnl.values, marker="o", label="PnL for BUY#1 (with fees)")
plt.axhline(0, color="black", linestyle="--", linewidth=1)
plt.title("Cumulative PnL for BUY#1 (with fees)")
plt.xlabel("Trade Index")
plt.ylabel("PnL")
plt.legend()
plt.tight_layout()

os.makedirs("out", exist_ok=True)
out_path = "out/pnl_curve_with_fees.png"
plt.savefig(out_path)
print(f"\nPnL curve saved to {out_path}")
