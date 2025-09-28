# experiments/backtest.py
import pandas as pd
import matplotlib.pyplot as plt
from experiments.train import model, X_test, y_test

# 简单策略：预测上涨就持有1单位
signals = model.predict(X_test)
returns = pd.Series(y_test).shift(-1).fillna(0)  # 下一步涨跌作为收益

pnl = (signals * returns).cumsum()

plt.plot(pnl)
plt.title("Strategy PnL")
plt.show()
