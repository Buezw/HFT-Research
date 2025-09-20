VENV = .venv
PYTHON = $(VENV)/bin/python

read_trades_py:
	@echo ">>> Activating venv and running Python script..."
	@$(PYTHON) py_strategy/read_trades.py

run_cpp:
	@echo ">>> Building and running C++ engine..."
	cmake -S engine_cpp -B build/engine_cpp -DCMAKE_BUILD_TYPE=Release
	cmake --build build/engine_cpp --config Release -j
	./build/engine_cpp/hft_engine
