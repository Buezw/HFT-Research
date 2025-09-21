#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <algorithm>
#include <onnxruntime_cxx_api.h>
#include "OrderBook.h"   // 撮合引擎
#include "MarketMaker.h" // 市场对手方模拟

int main() {
    // === 1. 初始化 ONNX Runtime ===
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "HFTSim");
    Ort::SessionOptions session_options;
    session_options.SetIntraOpNumThreads(1);
    Ort::Session session(env, "py_strategy/lstm_toy.onnx", session_options);

    MarketMaker mm; // 市场对手方

    // === 2. 打开 tick 数据 (CSV) ===
    std::ifstream fin("data/sample.csv");  // 格式: timestamp,price,volume
    if (!fin.is_open()) {
        std::cerr << "Error: could not open data/sample.csv" << std::endl;
        return -1;
    }

    std::string line;
    getline(fin, line); // 跳过表头

    // === 3. 初始化 OrderBook ===
    OrderBook ob;
    int next_id = 1;

    // === 4. 打开输出文件 ===
    std::ofstream fout("output.csv");
    fout << "timestamp,price,signal\n"; // 写表头

    // === 5. 逐 tick 推理 ===
    while (getline(fin, line)) {
        std::stringstream ss(line);
        std::string ts_str, price_str, volume_str;

        // 按逗号分隔
        getline(ss, ts_str, ',');
        getline(ss, price_str, ',');
        getline(ss, volume_str, ',');

        if (ts_str.empty() || price_str.empty() || volume_str.empty()) {
            continue; // 跳过不完整行
        }

        double price = std::stod(price_str);
        double volume = std::stod(volume_str);

        // === 5.1 模拟市场流动性 ===
        mm.injectLiquidity(ob, price, volume, next_id);

        // === 5.2 构造输入 (4个特征: price, volume, feat3, feat4) ===
        std::vector<float> input_data = {
            static_cast<float>(price),
            static_cast<float>(volume),
            0.0f,
            0.0f
        };
        std::vector<int64_t> input_shape = {1, 1, 4}; // batch=1, seq=1, features=4

        Ort::MemoryInfo mem_info = Ort::MemoryInfo::CreateCpu(
            OrtArenaAllocator, OrtMemTypeDefault
        );
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            mem_info,
            input_data.data(),
            input_data.size(),
            input_shape.data(),
            input_shape.size()
        );

        // === 5.3 模型推理 ===
        const char* input_names[] = {"input"};
        const char* output_names[] = {"output"};

        auto output_tensors = session.Run(
            Ort::RunOptions{nullptr},
            input_names, &input_tensor, 1,
            output_names, 1
        );

        float* output_arr = output_tensors.front().GetTensorMutableData<float>();
        size_t out_len = output_tensors.front().GetTensorTypeAndShapeInfo().GetElementCount();

        // === 6. 转换为交易信号 ===
        int signal_idx = std::max_element(output_arr, output_arr + out_len) - output_arr;

        if (signal_idx == 0) {
            std::cout << "[" << ts_str << "] Signal = BUY @ " << price << std::endl;
            ob.add_order({next_id++, "BUY", "LIMIT", price, 10});
        } else if (signal_idx == 1) {
            std::cout << "[" << ts_str << "] Signal = SELL @ " << price << std::endl;
            ob.add_order({next_id++, "SELL", "LIMIT", price, 10});
        } else {
            std::cout << "[" << ts_str << "] Signal = HOLD" << std::endl;
        }

        // === 7. 写入日志文件 ===
        fout << ts_str << "," << price << "," << signal_idx << "\n";

        // === 8. 打印订单簿状态 (可选) ===
        ob.print_book();
    }

    fout.close();
    fin.close();

    std::cout << "Simulation finished. Results saved to output.csv" << std::endl;
    return 0;
}
