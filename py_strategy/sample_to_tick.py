import pandas as pd
import numpy as np
import datetime
import os

# 读入日线数据
df = pd.read_csv("sample.csv")  # 你现有的日线文件
out_ticks = []

for idx, row in df.iterrows():
    date = row["Date"]
    open_p = row["AAPL.Open"]
    high_p = row["AAPL.High"]
    low_p = row["AAPL.Low"]
    close_p = row["AAPL.Close"]
    vol = int(row["AAPL.Volume"])

    # 每天模拟 N 个 ticks
    n_ticks = max(200, vol // 5000)  # tick 数量 ~ 成交量决定
    times = pd.date_range(f"{date} 09:30:00", f"{date} 16:00:00", periods=n_ticks)

    # 生成价格轨迹 (随机游走，限制在 high-low 范围)
    prices = np.linspace(open_p, close_p, n_ticks)  # 基础趋势
    noise = np.random.normal(0, (high_p - low_p) / 50, n_ticks)  # 随机波动
    prices = np.clip(prices + noise, low_p, high_p)

    # 生成成交量 (随机分配，总和 = Volume)
    volumes = np.random.multinomial(vol, [1/n_ticks]*n_ticks)

    # 拼装 tick 数据
    for t, p, v in zip(times, prices, volumes):
        out_ticks.append([t, p, v])

# 保存到 CSV
os.makedirs("out", exist_ok=True)
tick_df = pd.DataFrame(out_ticks, columns=["timestamp", "price", "volume"])
tick_df.to_csv("out/aapl_ticks.csv", index=False)

print("✅ Tick 数据已生成: out/aapl_ticks.csv")
