# experiments/train.py
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

from factors.engine import compute_factors
from models.linear.logistic import LogitModel

# ===== Step 1. 数据准备 =====
df = pd.read_csv("data/orderbook_top_ticks.csv")

# 拆分买卖盘，确保行数对齐
df_buy = df[df["side"] == "BUY"].reset_index(drop=True)
df_sell = df[df["side"] == "SELL"].reset_index(drop=True)

# 计算 midprice = (买一价 + 卖一价) / 2
df_mid = pd.DataFrame()
df_mid["ts_ns"] = df_buy["ts_ns"]
df_mid["midprice"] = (df_buy["price"] + df_sell["price"]) / 2
df_mid["close"] = df_mid["midprice"]   # 👈 兼容旧因子实现

# 定义标签：下一步 midprice 是否上涨
df_mid["y"] = (df_mid["midprice"].shift(-1) > df_mid["midprice"]).astype(int)

# ===== Step 2. 计算因子 =====
cfg = yaml.safe_load(open("configs/factors.yaml"))
factor_names = [f["name"] for f in cfg["factors"]]

X = compute_factors(df_mid, factor_names).fillna(0)
y = df_mid["y"].fillna(0)

# 如果没有算出任何因子，直接报错
if X.shape[1] == 0:
    raise ValueError("No factors were successfully computed. Check your factors/ implementation.")

# ===== Step 3. 切分训练/测试 =====
X_train, X_test, y_train, y_test = train_test_split(
    X, y, shuffle=False, test_size=0.2
)

# ===== Step 4. 选择模型 =====
model = LogitModel()  # 或者换成 XGBModel()
model.fit(X_train, y_train)

# ===== Step 5. 预测 & 评估 =====
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print("AUC:", roc_auc_score(y_test, y_prob))
