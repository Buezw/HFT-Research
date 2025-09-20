cmake_minimum_required(VERSION 3.20)
project(hftsim_engine CXX)

set(CMAKE_CXX_STANDARD 17)

# 撮合引擎
add_executable(hft_engine
    src/main.cpp
    src/OrderBook.cpp
)

# 策略 runner (ONNXRuntime)
add_executable(strategy_runner
    strategy_runner.cpp
    src/OrderBook.cpp
)

# ====== Include Path ======
# 本地头文件 (OrderBook.h, Order.h)
target_include_directories(hft_engine PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(strategy_runner PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

# ====== ONNXRuntime SDK ======
set(ONNXRUNTIME_DIR "$ENV{HOME}/onnxruntime-linux-x64-1.19.2")

# 手动包含 ONNXRuntime 头文件 & 库
target_include_directories(strategy_runner PRIVATE ${ONNXRUNTIME_DIR}/include)
target_link_libraries(strategy_runner PRIVATE ${ONNXRUNTIME_DIR}/lib/libonnxruntime.so)
