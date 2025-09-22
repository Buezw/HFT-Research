# 📈 HFTSim – High-Frequency Trading Simulator

HFTSim is a compact, extensible **high-frequency trading (HFT) simulation stack** for research and demos.
It combines a **C++ limit-order-book engine**, **Python/ONNX strategy inference (via ONNX Runtime from C++)**, and **Streamlit dashboards** for monitoring and post-trade review.

* Fast C++ matching loop with optional market-maker flow
* Plug-in ML strategies exported to **ONNX**
* Tick generation from coarse OHLC data for sandboxed experiments
* Two UIs:

  * **Monitoring** (lightweight) – price + signals
  * **Industrial Review** – PnL, drawdown, Sharpe, slippage, turnover, etc.

---

## 📂 Repository layout

```
HFTSim/
├── configs/                    # YAML runtime knobs (fees, slippage, etc.)
│   └── run.yaml
├── data/                       # Inputs & outputs (csv)
│   ├── origin.csv                   # Raw daily OHLCV (e.g., AAPL)
│   ├── orderbook_top_ticks.csv      # Simulated tick stream (best bid/ask events)
│   ├── signals_buy.csv              # Model signals per tick (timestamp, price, signal)
│   ├── trades_executed.csv          # Your executed trades (side, qty, price, ts)
│   ├── orderbook_snapshot.csv       # (debug) book snapshots
│   └── trades.csv                   # (debug) global trade tape
├── engine_cpp/                  # C++ engine + ONNX inference
│   ├── include/
│   │   ├── OrderBook.h
│   │   └── MarketMaker.h
│   ├── src/
│   │   ├── OrderBook.cpp
│   │   └── ...
│   ├── strategy_runner.cpp          # Loads ONNX, streams ticks, places orders
│   └── CMakeLists.txt
├── py_strategy/                 # Python utilities / model export
│   ├── tickify.py                   # Make synthetic ticks from daily OHLCV
│   ├── export_model.py              # Example: export to ONNX
│   └── lstm_toy.onnx               # Example ONNX model
├── dashboard.py                  # Live monitoring (simple)
└── dashboard_review.py           # Industrial post-trade review
```

---

## 🔧 Requirements

**System**

* Linux/macOS (tested on Linux)
* CMake ≥ 3.18, a recent C++ compiler (GCC ≥ 9/Clang ≥ 10)
* **ONNX Runtime C/C++** libraries installed and discoverable by CMake (or set `ONNXRUNTIME_DIR`)

**Python**

* Python 3.9+
* `pip install -r requirements.txt` (or install manually):

  ```
  streamlit pandas numpy altair
  ```

**(optional)** Conda

```bash
conda create -n hftsim python=3.9 -y
conda activate hftsim
pip install -r requirements.txt
```

---

## 🚀 Quick start

### 1) Prepare data

Place a daily OHLCV CSV at `data/origin.csv` (e.g., AAPL). Columns like:

```
Date, AAPL.Open, AAPL.High, AAPL.Low, AAPL.Close, AAPL.Volume, ...
```

### 2) Generate synthetic ticks

Turn daily bars into a short tick stream for sandbox runs:

```bash
python py_strategy/tickify.py \
  --in data/origin.csv \
  --out data/orderbook_top_ticks.csv \
  --symbol AAPL \
  --seconds 1.0         # how long to simulate (wall-clock span)
  --bps 2               # spread/tweak knobs (example)
```

This produces `data/orderbook_top_ticks.csv` with columns:

```
ts_ns,side,price,qty
1600000000...,BUY,127.48,8440
...
```

Each timestamp is **nanoseconds**; two rows with the same `ts_ns` represent best-bid and best-ask changes at that instant.

### 3) Build the C++ engine

```bash
cmake -S engine_cpp -B build/engine_cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/engine_cpp --config Release -j
```

### 4) Run the strategy + engine

```bash
./build/engine_cpp/strategy_runner
```

Outputs (non-blocking, batched at the end):

* `data/signals_buy.csv`  — `timestamp,price,signal` (0=BUY,1=SELL,2=HOLD or mapped)
* `data/trades_executed.csv` — `ts_ns,side,price,qty,buy_id,sell_id`

**Debug mode:** in `engine_cpp/strategy_runner.cpp`

```cpp
static constexpr bool DEBUG_MODE = false;  // set true to see prints & extra logs
```

When `true` you’ll also get `orderbook_snapshot.csv` and `data/trades.csv` (useful for debugging, not for speed tests).

### 5) Post-trade review dashboard

Industrial-style PnL & execution analytics:

```bash
streamlit run dashboard_review.py
```

What you’ll see:

* **Cumulative PnL** (aggregated by 10ms/100ms/1s/1min – auto-selected)
* **Key metrics**: Final PnL, Max Drawdown, Sharpe (approx), Hit Rate, Turnover, Avg/Median Slippage
* **Volume over time** (aggregated)
* **Net position curve**
* **Slippage distribution**

### 6) (Optional) Live monitoring dashboard

Lightweight price + signals overlay:

```bash
streamlit run dashboard.py
```

---

## 🧠 Strategy integration (ONNX)

* The runner loads `py_strategy/lstm_toy.onnx` and performs inference **inside the C++ loop** with ONNX Runtime.
* Make sure the model I/O names match in `strategy_runner.cpp`:

  ```cpp
  const char* in_names[]  = {"input"};
  const char* out_names[] = {"output"};
  ```
* Input features (example): `[price, qty, is_buy, 0.0]`. Adjust as you see fit.
* Export your own model to ONNX via `py_strategy/export_model