# 📈 HFTSim – High-Frequency Trading Simulator (Detailed English README)

HFTSim is a **compact, extensible HFT research and demo stack**.
It combines a **C++ limit-order-book engine**, **strategy inference via ONNX Runtime (from C++)**, and a **Python web UI** for **factor/model exploration** plus **Streamlit dashboards** for post-trade review.

---

## ✨ What’s implemented

* **C++ limit order book** with optional market-maker flow (event-driven, micro/millisecond scale)
* **ONNX inference inside C++** using ONNX Runtime (no Python in the hot path)
* **Data sandbox**: turn daily OHLCV into synthetic **best bid/ask tick streams**
* **Factor system**

  * Auto-discovery & auto-registration (`factors/__init__.py`)
  * Each factor ships **description / formula (LaTeX) / explanation**
  * One-click compute & Plotly visualization
* **Model system**

  * Unified **model registry** (`models/base.py`) with `name/desc/task/class`
  * Supports **classification** and **regression**
  * Web UI: pick a model, train, and get **Accuracy/AUC/ROC** (classification) or **MSE/R²** (regression)
* **Interactive web app (FastAPI + Jinja2 + Plotly)**

  * Left: **category cards** → pick a factor
  * Center: **factor details + time series**
  * Right: **model selection + training results + ROC**
* **Streamlit review dashboard**

  * Industrial metrics: PnL, Max Drawdown, Sharpe (approx), Hit Rate, Turnover, Slippage distribution, etc.
* **Engineering-friendly**

  * Clear layout, config, data flow, APIs, and extension patterns

---

## 📂 Repository layout

```
HFTSim/
├── app.py                         # FastAPI service (factor/model explorer)
├── templates/
│   └── index.html                 # Jinja2 + Plotly front-end
├── static/                        # Optional static assets
│
├── factors/                       # Factor framework (auto-discovery)
│   ├── __init__.py                # walk_packages auto-imports to trigger registration
│   ├── base.py                    # registry, decorator, metadata
│   ├── engine.py                  # compute_factors(df, factor_list)
│   ├── price/
│   │   └── momentum.py            # momentum_5, momentum_20 (with formula/explanation)
│   └── ...                        # add more categories/files
│
├── models/                        # Model framework (auto-discovery)
│   ├── __init__.py
│   ├── base.py                    # registry, task type (classification/regression)
│   ├── linear/
│   │   └── logistic.py            # LogitModel (scikit-learn LogisticRegression)
│   └── tree/
│       └── xgb.py                 # XGBoost example (optional)
│
├── experiments/
│   ├── train.py                   # CLI training example
│   └── backtest.py                # simple backtest stub
│
├── engine_cpp/                    # C++ engine + ONNX inference
│   ├── include/                   # OrderBook/MarketMaker headers
│   ├── src/                       # matching & I/O
│   ├── strategy_runner.cpp        # loads ONNX, streams ticks, makes orders
│   └── CMakeLists.txt
│
├── py_strategy/                   # Python helpers (export to ONNX, tickify, etc.)
│   ├── export_model.py
│   ├── tickify.py                 # build synthetic best bid/ask ticks
│   └── lstm_toy.onnx              # example ONNX
│
├── data/
│   ├── origin.csv                 # raw daily OHLCV (e.g., AAPL)
│   ├── orderbook_top_ticks.csv    # synthetic top-of-book ticks (ts_ns, side, price, qty)
│   ├── signals_buy.csv            # strategy signals (timestamp, price, signal)
│   ├── trades_executed.csv        # executed trades (ts_ns, side, price, qty, ...)
│   └── ...                        # optional debug outputs
│
├── dashboard.py                   # lightweight live monitor
└── dashboard_review.py            # industrial post-trade analytics
```

---

## 🔧 Requirements

### System

* Linux/macOS (primarily tested on Linux)
* CMake ≥ 3.18, GCC ≥ 9 / Clang ≥ 10
* **ONNX Runtime C/C++** installed and discoverable by CMake (or set `ONNXRUNTIME_DIR`)

### Python

* Python 3.9+
* Recommended:

  ```bash
  conda create -n hftsim python=3.9 -y
  conda activate hftsim
  ```
* Install packages (adjust as needed):

  ```bash
  pip install fastapi uvicorn jinja2 pandas numpy scikit-learn plotly pyyaml
  # optional:
  # pip install xgboost lightgbm catboost streamlit
  ```

---

## 🔩 Data pipeline & labels

### Input: `data/orderbook_top_ticks.csv`

```
ts_ns,side,price,qty
160000000000197079,BUY,127.48,8440
160000000000197079,SELL,127.50,8440
...
```

* `ts_ns`: nanosecond timestamp; often a BUY/SELL pair per instant (best bid/ask update)
* `price`: top-of-book price
* `qty`: size on that side

### Midprice construction

If `midprice` isn’t present, the app constructs it:

* If `bid/ask` present: `midprice = (bid + ask) / 2`
* Else fallback to `price` if only trades are available

### Default label (simple demo)

* Binary next-tick direction:
  `y = (midprice_{t+1} > midprice_t)`
* In true HFT, this **has extremely low signal**; AUC ≈ 0.5 is common.
* Practical variants:

  * Predict farther horizon (`t + N`)
  * Aggregate over fixed time/volume windows
  * Thresholded returns / take-profit / stop-loss style labels

---

## 🧱 Factor system

### Registration & auto-discovery

* `factors/base.py` exposes a registry and decorator
* `factors/__init__.py` uses `pkgutil.walk_packages` to import all submodules and trigger registration

**Example – `factors/price/momentum.py`**

```python
import pandas as pd
from factors.base import register_factor

@register_factor(
    name="momentum_5",
    category="price",
    desc="5-tick momentum",
    formula=r"Momentum_5(t) = \frac{P_t}{P_{t-5}} - 1",
    explanation="Measures the percentage price change over the past 5 ticks."
)
def momentum_5(df: pd.DataFrame) -> pd.Series:
    return df["midprice"].pct_change(5)

@register_factor(
    name="momentum_20",
    category="price",
    desc="20-tick momentum",
    formula=r"Momentum_20(t) = \frac{P_t}{P_{t-20}} - 1",
    explanation="Measures the percentage price change over the past 20 ticks."
)
def momentum_20(df: pd.DataFrame) -> pd.Series:
    return df["midprice"].pct_change(20)
```

**Compute – `factors/engine.py`**

```python
def compute_factors(df: pd.DataFrame, factor_list=None) -> pd.DataFrame:
    """
    Compute requested factors; returns a DataFrame whose columns are factor names.
    """
    ...
```

---

## 🤖 Model system

### Registration & auto-discovery

* `models/base.py` maintains the registry with:

  ```python
  {"name", "desc", "task", "class"}
  ```
* `task` is `"classification"` or `"regression"`
* `models/__init__.py` auto-imports submodules to trigger registration

**Registry – `models/base.py`**

```python
MODEL_REGISTRY = {}

def register_model(name: str, desc: str, task: str = "classification"):
    def decorator(cls):
        MODEL_REGISTRY[name] = {
            "name": name,
            "desc": desc,
            "task": task,
            "class": cls,
        }
        return cls
    return decorator

def get_all_models():
    return MODEL_REGISTRY
```

**Example – Logistic Regression `models/linear/logistic.py`**

```python
import pandas as pd
from sklearn.linear_model import LogisticRegression
from models.base import register_model

@register_model(name="logit", desc="Logistic Regression classifier", task="classification")
class LogitModel:
    def __init__(self):
        self.clf = LogisticRegression(max_iter=200)

    def fit(self, X: pd.DataFrame, y):
        return self.clf.fit(X, y)

    def predict(self, X: pd.DataFrame):
        return self.clf.predict(X)

    def predict_proba(self, X: pd.DataFrame):
        return self.clf.predict_proba(X)  # shape [n, 2]
```

---

## 🌐 Web app (FastAPI + Plotly)

### Run

```bash
uvicorn app:app --reload --port 8000
```

### Endpoints

* `GET /` → index page (Jinja2 + Plotly)
* `GET /api/factors` → all factors **grouped by category** (with desc/formula/explanation)
* `GET /api/models` → model metadata (JSON-safe; class objects are not returned)
* `GET /api/compute?factor=<name>` → compute a factor time series `{x, y}`
* `GET /api/train?factor=<name>&model=<name>` → train & evaluate

  * Classification: `accuracy`, `auc`, `roc(fpr/tpr)`
  * Regression: `mse`, `r2`

### Training (core logic in `app.py`)

```python
meta = model_registry[model]            # {"name","desc","task","class"}
clf = meta["class"]()
clf.fit(X_train, y_train)
y_pred = clf.predict(X_test)

if meta["task"] == "classification":
    if hasattr(clf, "predict_proba"):
        y_prob = clf.predict_proba(X_test)
        y_prob = y_prob[:, 1] if (y_prob.ndim == 2 and y_prob.shape[1] > 1) else y_prob.ravel()
    else:
        y_prob = y_pred
    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    return {...}
else:
    mse = mean_squared_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)
    return {...}
```

### Front-end UX (`templates/index.html`)

* **Left**: factor **category cards** → click to reveal factors in the category
* **Center**: factor **details** (desc/formula/explanation) + **time series plot**
* **Right**: **model selection**, **Train** button, metrics, and **ROC** plot

---

## 🚀 Quick start

1. Put a daily OHLCV CSV in `data/origin.csv` (e.g., columns like `Date,AAPL.Open,AAPL.High,AAPL.Low,AAPL.Close,AAPL.Volume`).

2. Build synthetic top-of-book ticks:

```bash
python py_strategy/tickify.py \
  --in data/origin.csv \
  --out data/orderbook_top_ticks.csv \
  --symbol AAPL \
  --seconds 1.0 \
  --bps 2
```

3. Launch the web app:

```bash
uvicorn app:app --reload --port 8000
```

4. Open `http://127.0.0.1:8000`

   * Pick a category → pick a factor → see the time series
   * Pick a model → **Train** → see Accuracy/AUC/ROC (or MSE/R²)

---

## 📐 Working with large CSVs (e.g., 4M rows)

* **Preview downsampling** in `/api/compute`: uniformly sample points before sending to the browser
* **Time slicing** in `/api/train`: train/test on windows; parameterize horizon and sample sizes
* **Chunked factor calc**: compute + cache in chunks (Parquet/Arrow work well)
* **Vectorization first**: keep factor code NumPy/pandas-vectorized; avoid Python loops
* **Front-end simplification**: Plotly down-sampling or `simplify: true` on traces

---

## 🧩 Extending the system

### Add a new factor

1. Create a file under `factors/<category>/`
2. Implement a function and decorate with `@register_factor(...)`
3. Restart (or rely on auto-reload); it will appear in the left navigation

**Template**

```python
@register_factor(
    name="my_factor",
    category="liquidity",
    desc="My custom factor",
    formula=r"... LaTeX ...",
    explanation="What it measures and why it matters."
)
def my_factor(df: pd.DataFrame) -> pd.Series:
    ...
```

### Add a new model

1. Create a file under `models/<family>/`
2. Implement a class with `fit/predict` (and `predict_proba` for classifiers)
3. Decorate with `@register_model(name, desc, task)`

**Template**

```python
@register_model(name="rf", desc="Random Forest", task="classification")
class RandomForestModel:
    def __init__(self):
        self.clf = RandomForestClassifier(n_estimators=200, random_state=42)
    def fit(self, X, y): return self.clf.fit(X, y)
    def predict(self, X): return self.clf.predict(X)
    def predict_proba(self, X): return self.clf.predict_proba(X)
```

---

## 📊 Review dashboards (Streamlit)

```bash
streamlit run dashboard_review.py
```

You’ll get:

* **Cumulative PnL** (auto-selects aggregation: 10ms/100ms/1s/1min)
* **Key metrics**: Final PnL, Max Drawdown, Sharpe (approx), Hit Rate, Turnover, slippage stats
* **Volume over time**, **net position curve**, **slippage distribution**

---

## 🧠 Tips & gotchas

* **AUC ≈ 0.5 is not a bug** in HFT: next-tick direction is nearly random.
  Try **longer horizons**, **multi-factor features**, and **non-linear models**.
* **Feature scaling**: factor magnitudes can vary wildly (10^10 vs 10^-10).
  Consider standardization / quantile transform before modeling.
* **No leakage**: always use `train_test_split(..., shuffle=False)` for time series (we do).
* **Explainability**: keep each factor’s `desc/formula/explanation` complete for provenance.

---

## 🔭 Roadmap (practical next steps)

* Factor diagnostics: **histogram / autocorr / cross-corr** panels
* Factor cache + **parallel** computation
* Model **CV** + grid/Bayesian search
* Front-end **multi-factor selection** + **feature importance** (Permutation/SHAP)
* Engine: **latency model**, order life-cycle (place/cancel/partial fill)

---

## ❓ FAQ

**Q: I get AUC = 0.5 / Accuracy = 0.5. Is something broken?**
A: Not necessarily. With next-tick labels the signal is extremely weak.
Use longer horizons, more factors, and non-linear models (XGBoost/RF/SVM).

**Q: My CSV has 4M rows and the browser freezes.**
A: Downsample in `/api/compute`, train on windows, and consider chunked factor computation with caching.

**Q: How do I integrate my own strategy into the C++ engine?**
A: Export to ONNX in Python, ensure I/O names match in `strategy_runner.cpp`, then feed features (e.g., `[price, qty, is_buy, ...]`) through ONNX Runtime inside the C++ loop.

---

If you’d like, I can also provide ready-to-use snippets for **multi-factor training**, **factor distribution plots**, or **factor caching**—just say the word.
