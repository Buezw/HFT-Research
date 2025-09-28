# experiments/train.py
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

from factors.engine import compute_factors
from models.linear.logistic import LogitModel

# ===== Step 1. 数据 & 因子 =====
df = pd.read_csv("data/orderbook_top_ticks.csv")

cfg = yaml.safe_load(open("configs/factors.yaml"))
factor_names = [f["name"] for f in cfg["factors"]]

X = compute_factors(df, factor_names).fillna(0)
y = (df["close"].shift(-1) > df["close"]).astype(int)  # 简单涨跌标签

# ===== Step 2. 切分训练/测试 =====
X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)

# ===== Step 3. 选择模型 =====
model = LogitModel()  # 或 XGBModel()
model.fit(X_train, y_train)

# ===== Step 4. 预测 & 评估 =====
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print("AUC:", roc_auc_score(y_test, y_prob))
