# HFTSim TODO & Roadmap (中文)

> 目标：把“训练/回测/可视化/上线”全链条做成**可复现、可观察、可发布**的工程化方案。  
> 约定：打勾 `✅` / 未完成 `⬜`；优先级 `P0>P1>P2>P3`。负责人/截止时间可后续填充。

---

## 0) 当前状态快照（2025-09）

- ✅ FastAPI 只做 **API 调度**（子进程 `subprocess` 调 CLI），无训练逻辑
- ✅ `experiments/` 提供 **train/backtest** CLI；训练产物落到 `artifacts/<timestamp>_*`（`model.joblib / X_test.parquet / y_test.parquet / meta.json / backtest.json`）
- ✅ 前端可：选因子→训练（ROC/metrics）→回测（Test 1/6 的 **PnL** + **Prob vs Truth**）
- ✅ 数据：`data/orderbook_top_ticks.csv`；默认标签 `horizon` + `eps` 支持
- ⬜ 代码化：Drawdown/PR/Calibration 等更多诊断已给出补丁，待集成到主分支
- ⬜ C++ 引擎（`engine_cpp/`）：ONNX 前向已具备；待接入“盘中自适应层”（缩放/阈值/规模/风控）

---

## 1) 立即要做（P0）

### 1.1 回测与可视化增强
- ⬜ **加入更多面板**：Drawdown 曲线、Precision–Recall + AP、Calibration + Brier、Confusion Matrix、收益分布直方图  
  - **验收**：`/api/backtest` 返回新增字段；前端出现 3 张新图（Drawdown / PR / Calibration），并在面板显示 `AP / Brier / MDD / Sharpe_step`。
- ⬜ **交易成本/滑点**参数化：`fee`、`bps_slippage`、`latency_ticks`（简单模型）  
  - **验收**：`pnl` 计算中扣减成本；前端显示“含成本/不含成本”切换。

### 1.2 阈值与评估
- ⬜ **阈值在验证集上选择**，不要用测试集（避免泄漏）  
  - **验收**：`train.py` 切 `train/val/test = 4/1/1`，阈值来自 `val`；`backtest.py` 只读阈值，不再重算。
- ⬜ **长短双阈值**（可空仓）：`long_if p>th_long ; short_if p<th_short ; else flat`  
  - **验收**：`signals ∈ {-1,0,1}`；前端多一张 **Net Position** 曲线。

### 1.3 工程健壮性
- ⬜ **Parquet 依赖**：在 README/错误信息中明确 `pyarrow` 依赖；无则回退 CSV（性能较差）  
- ⬜ **统一随机种子**（训练/切分/模型）以便复现  
- ⬜ **API 错误气泡**：把子进程 stderr 原样带回前端（已基本具备），并在 UI 中红色提示  
- ⬜ **Artifacts 结构规范**：`artifacts/<ts>_<tag>/{meta.json, model.joblib, scaler.joblib?, X_test.parquet, y_test.parquet, backtest.json, metrics/plots/}`  
- ⬜ **时间轴可读化**：纳秒 `ts_ns` 转人类可读（ms/s）；前端 hover 显示格式化时间

---

## 2) 近期（P1）

### 2.1 盘中自适应层（C++，不改权重）
- ⬜ **在线缩放**：EWM/Welford 维护均值方差；与训练尺度一致或明确在模型外统一缩放  
- ⬜ **自适应阈值**：维护近 N 分钟分数分布，按目标触发率设 `threshold = Q_q(scores)`  
- ⬜ **规模控制**：`size ∝ 1/vol_t` 或 `∝ book_depth`；加入最小手数与上限  
- ⬜ **风控**：持仓上限、单笔/累计滑点、实时 PnL/Kill-switch，异常熔断  
- **验收**：`strategy_runner.cpp` 前后插钩子；有独立单元测试与仿真脚本

### 2.2 训练与发布
- ⬜ **夜间重训作业**：最近 K 天滚动重训；保存 `model.onnx`、`feature_order.json`、`schema.json`  
- ⬜ **影子验证/金丝雀**：盘前把新权重在昨日数据回放，对比关键 KPI；允许快速回滚  
- ⬜ **ONNX 热加载**：安全切换（双缓冲、版本号）

### 2.3 特征与模型
- ⬜ **多因子库**：OFI（Order Flow Imbalance）、microprice 偏移、spread、depth、短期波动率（EWM/RS）、成交量/力度等  
- ⬜ **并行/缓存**：因子计算 `joblib`/多进程 + Parquet 缓存（分窗/分日）  
- ⬜ **模型扩展**：XGBoost、RandomForest、线性回归（回归任务）；分类加 `class_weight="balanced"` 选项  
- ⬜ **特征选择与正则**：L1/L2，或基于 permutation importance

---

## 3) 中期（P2）

### 3.1 漂移与健康度监控
- ⬜ **输入分布漂移**：PSI/KS/分位差；阈值告警  
- ⬜ **性能健康**：AUC/AP/命中率/触发率/滑点/成交率/收益回撤；Prometheus 指标 + Grafana 面板  
- ⬜ **自动化回退**：触发阈值自动提高 `threshold`、降规模或回滚模型

### 3.2 验证方式
- ⬜ **滚动 Walk-Forward**：窗口化 `train→val→test` 循环，聚合多段指标  
- ⬜ **时变成本**：从数据估计 `spread/impact`，更贴近实盘

### 3.3 前端/UX
- ⬜ 阈值滑条 + 即时重绘（阈值→信号→PnL）  
- ⬜ 切换“含/不含成本”“做多/做空/双向”  
- ⬜ 结果导出：CSV/PNG/JSON 一键下载

---

## 4) 远期（P3）

- ⬜ **在线学习/自适应模型**：Bandit/BLR/Kalman/partial_fit（严格风控与回滚）  
- ⬜ **延迟模型**：撮合与排队延迟、撤单延迟，纳入策略决策  
- ⬜ **部署**：容器化 + CI/CD（单测、lint、build、发布工件）  
- ⬜ **文档**：系统图、特征/模型/工程最佳实践、FAQ

---

## 附录 A：关键验收标准（示例）

- **回测 JSON 模式**：  
  ```json
  {
    "threshold": 0.27,
    "series": {
      "ts": ["1600000..."],
      "pnl": [...],
      "drawdown": [...],
      "y_prob": [...],
      "y_test": [...]
    },
    "risk": {"max_drawdown": -0.12, "sharpe_step": 0.18, "exposure": 0.42, "turnover": 85},
    "classification": {"precision_at_threshold": 0.31, "recall_at_threshold": 0.22, "f1_at_threshold": 0.26, "average_precision": 0.34, "brier": 0.24},
    "curves": {"pr": {"precision": [...], "recall": [...]}, "calibration": {"mean_pred": [...], "frac_pos": [...]}},
    "ret_hist": {"edges": [...], "counts": [...]}
  }
  ```

- **自适应层接口**（C++，示意）：  
  ```cpp
  struct OnlineScaler { double mean, var; void update(double x); double transform(double x) const; };
  double adaptive_threshold(const std::vector<double>& scores, double q);
  double position_size(double vol);
  ```

---

## 附录 B：常用命令

- 训练（固定 5:1 切分 → `test_size=1/6`）：  
  ```bash
  python -m experiments.train \
    --data data/orderbook_top_ticks.csv \
    --model logit \
    --factors momentum_5 \
    --horizon 5 --eps 0.0 --drop_equal --scale \
    --test_size 0.1667 \
    --outdir artifacts/run_$(date +%Y%m%d_%H%M%S)
  ```

- 回测（读 artifacts）：  
  ```bash
  python -m experiments.backtest \
    --artdir artifacts/XXXX_logit_momentum_5_h5_e0.0 \
    --data data/orderbook_top_ticks.csv \
    --horizon 5 --json artifacts/XXXX_logit_momentum_5_h5_e0.0/backtest.json
  ```

---

## 附录 C：任务清单（可复制到 issue tracker）

- [ ] P0: 集成 Drawdown/PR/Calibration/Confusion Matrix 可视化与指标
- [ ] P0: 成本模型（fee/滑点/延迟）接入回测
- [ ] P0: 阈值在验证集上选择（train/val/test = 4/1/1），测试集只评估
- [ ] P0: Artifacts 目录结构规范与 README 更新；时轴格式化
- [ ] P1: C++ 盘中自适应层：在线缩放/动态阈值/规模/风控钩子
- [ ] P1: 夜间重训流水线（导出 ONNX、影子验证、热加载、回滚）
- [ ] P1: 多因子扩展 + 并行与缓存
- [ ] P2: 漂移与健康监控（Prometheus/Grafana）
- [ ] P2: Walk-Forward 验证与时变成本
- [ ] P3: 在线学习探索、延迟模型、CI/CD、完整文档
