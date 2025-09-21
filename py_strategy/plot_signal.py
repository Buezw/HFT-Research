import pandas as pd
import matplotlib.pyplot as plt
import os

# === 1. 读取数据 ===
signals = pd.read_csv("output.csv")          # timestamp,price,signal
trades = pd.read_csv("trades.csv")           # ts_ns,buy_id,sell_id,price,qty
book = pd.read_csv("orderbook_snapshot.csv")      # ts_ns,side,price,qty

# === 2. 转换时间戳 ===
# output.csv 里 timestamp -> datetime
# === 2. 转换时间戳 ===
signals['timestamp'] = pd.to_datetime(signals['timestamp'])
trades['timestamp'] = pd.to_datetime(trades['ts_ns'], unit='ns')
book['timestamp']   = pd.to_datetime(book['ts_ns'], unit='ns')


# trades.csv 和 book_snapshot.csv 里的 ts_ns 是纳秒整数 -> datetime
trades['timestamp'] = pd.to_datetime(trades['ts_ns'])
book['timestamp'] = pd.to_datetime(book['ts_ns'])

# === 3. 筛选信号点 ===
buy_signals = signals[signals['signal'] == 0]
sell_signals = signals[signals['signal'] == 1]

# === 4. 从盘口提取买一/卖一价 ===
best_bids = book[book['side'] == "BUY"].groupby("timestamp")["price"].max().reset_index()
best_asks = book[book['side'] == "SELL"].groupby("timestamp")["price"].min().reset_index()

# === 5. 创建输出目录 ===
os.makedirs("out", exist_ok=True)

# === 6. 绘图 ===
plt.figure(figsize=(14, 7))

# 策略价格曲线
plt.plot(signals['timestamp'], signals['price'], label="Mid Price", color="black", alpha=0.6)

# BUY/SELL 信号
plt.scatter(buy_signals['timestamp'], buy_signals['price'], color="green", marker="^", s=60, label="BUY Signal")
plt.scatter(sell_signals['timestamp'], sell_signals['price'], color="red", marker="v", s=60, label="SELL Signal")

# 成交点（蓝色）
plt.scatter(trades['timestamp'], trades['price'], color="blue", marker="o", s=20, alpha=0.5, label="Trades")

# 买一卖一
plt.plot(best_bids['timestamp'], best_bids['price'], label="Best Bid", color="green", linestyle="--", alpha=0.7)
plt.plot(best_asks['timestamp'], best_asks['price'], label="Best Ask", color="red", linestyle="--", alpha=0.7)

# 美化
plt.title("Strategy Signals + Trades + OrderBook Snapshot")
plt.xlabel("Time")
plt.ylabel("Price")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()

# === 7. 保存 ===
out_path = os.path.join("out", "market_overview.png")
plt.savefig(out_path, dpi=300)
print(f"✅ Plot saved to {out_path}")
