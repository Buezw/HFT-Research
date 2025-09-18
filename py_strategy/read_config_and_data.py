import yaml
import pandas as pd

# 1. 读取配置文件
with open("../configs/run.yaml", "r") as f:
    cfg = yaml.safe_load(f)

print("=== Configs Loaded ===")
print(cfg)

# 2. 读取数据文件
data_path = cfg["data"]["path"]
try:
    df = pd.read_csv("../" + data_path)
    print("\n=== Data Loaded ===")
    print(df.head())   # 打印前5行
except FileNotFoundError:
    print(f"\nData file not found: {data_path}")



import matplotlib.pyplot as plt
import os

# 假设数据里有 AAPL.Close
if "AAPL.Close" in df.columns:
    os.makedirs("out", exist_ok=True)  # 确保输出目录存在

    plt.figure(figsize=(10,5))
    plt.plot(df["Date"], df["AAPL.Close"], label="AAPL Close Price")
    plt.xticks(rotation=45)
    plt.title("AAPL Closing Price Over Time")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.tight_layout()

    # 保存图片
    out_path = "out/closing_price.png"
    plt.savefig(out_path)
    print(f"\nPlot saved to {out_path}")

