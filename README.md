# HFTSim – High-Frequency Trading Simulator

HFTSim is a simplified yet extensible **high-frequency trading (HFT) simulation system** designed for research and demonstration.
It integrates a **C++ matching engine**, **Python strategy prototyping**, and **ONNX Runtime for model inference**, with planned future extensions toward **FPGA acceleration**.

---

## 📂 Project Structure

```
HFTSim/
├── configs/               # YAML config files (trading parameters, fees, slippage, etc.)
│   └── run.yaml
├── data/                  # Sample market data (CSV)
│   └── sample.csv
├── docs/                  # Documentation
├── engine_cpp/            # Core C++ engine
│   ├── include/           # Header files
│   │   ├── Order.h        # Order structure
│   │   └── OrderBook.h    # Matching engine class (declaration)
│   ├── src/               # Implementation files
│   │   ├── main.cpp       # Simple demo runner
│   │   └── OrderBook.cpp  # Matching engine implementation
│   ├── strategy_runner.cpp # Loads ONNX model + simulates trading decisions
│   └── CMakeLists.txt     # Build configuration
├── py_strategy/           # Python-based research & model training
│   ├── read_config_and_data.py  # Loads configs & market data
│   ├── export_model.py          # Example: export model to ONNX
│   └── lstm_toy.onnx            # Example LSTM model
├── verilog/               # (Planned) FPGA modules
│   └── nanotimer.v        # Example placeholder for nanosecond timer
└── README.md
```

---

## ⚙️ Components

### 1. **C++ Matching Engine (`engine_cpp/`)**

* Implements a **limit order book** with:

  * BUY/SELL orders
  * Market and limit order matching
  * Order cancellation
* **Nanosecond-level timestamps** for trades
* Logs trades into CSV for later analysis

### 2. **Python Strategy Layer (`py_strategy/`)**

* Loads and preprocesses historical market data
* Prototypes trading logic and trains models (e.g., LSTM)
* Exports trained strategies as **ONNX models** for fast inference

### 3. **ONNX Runtime Integration**

* The C++ `strategy_runner` loads ONNX models
* Runs model inference directly inside the matching loop
* Bridges Python prototyping with low-latency C++ execution

### 4. **Configuration (`configs/run.yaml`)**

* Controls trading parameters:

  * Tick size
  * Fee schedule (maker/taker bps)
  * Slippage assumptions
  * Data path
  * Matching engine behavior

### 5. **Data (`data/sample.csv`)**

* Demo market data for simulation
* Easily replaceable with other datasets

---

## 🚀 How to Build & Run

```bash
# From project root
cmake -S engine_cpp -B build/engine_cpp -DCMAKE_BUILD_TYPE=Release
cmake --build build/engine_cpp --config Release -j

# Run the simple matching engine
./build/engine_cpp/hft_engine

# Run the strategy runner with ONNX model
./build/engine_cpp/strategy_runner
```

---

## 📊 Example Output

```
TRADE: 5 @ 100.5 between BUY#1 and SELL#2
TRADE: 5 @ 101 between BUY#1 and SELL#3
MARKET BUY TRADE: 2 @ 101 with SELL#3
MARKET order unfilled qty: 6 discarded.
```

And when running the ONNX strategy:

```
Model raw output: 0 0.995055
Signal = HOLD
```

---

## 🔮 Future Work: FPGA Acceleration

A future extension of **HFTSim** is to integrate **FPGA (Field-Programmable Gate Array)** hardware acceleration for ultra-low-latency trading.

### Why FPGA?

* Sub-microsecond latency (nanosecond precision)
* True hardware-level parallelism
* Industry-standard for colocation trading

### Planned FPGA Modules

* **Market data parser** (decode exchange feeds directly in hardware)
* **Order matching pipeline** (replicating `OrderBook` logic in Verilog)
* **Risk checks & throttling**
* **Nanosecond timer** (see `verilog/nanotimer.v` as a placeholder)

### Target Hardware

* **Xilinx Alveo (U50/U250/U280)**
* **Intel Stratix 10 / Agilex**

These cards connect via PCIe and can directly interact with low-latency NICs (e.g., Exablaze/Solarflare).

---

## 📝 License

MIT License (to be updated if extended with external libraries).

---
