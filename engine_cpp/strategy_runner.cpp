#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <onnxruntime_cxx_api.h>
#include "OrderBook.h"   // 你已有的撮合引擎

int main() {
    // === 1. 初始化 ONNX Runtime ===
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "HFTSim");
    Ort::SessionOptions session_options;
    session_options.SetIntraOpNumThreads(1);
    Ort::Session session(env, "py_strategy/lstm_toy.onnx", session_options);

    // === 2. 打开行情数据 (CSV) ===
    std::ifstream fin("data/sample.csv");
    if (!fin.is_open()) {
        std::cerr << "Error: could not open data/sample.csv" << std::endl;
        return -1;
    }

    std::string line;
    getline(fin, line); // 跳过表头

    // === 3. 初始化 OrderBook ===
    OrderBook ob;
    int next_id = 1;

    // === 4. 逐行读取数据并推理 ===
    while (getline(fin, line)) {
        std::stringstream ss(line);
        double ts, price, volume;
        ss >> ts >> price >> volume;  // 假设 CSV: timestamp price volume

        // 构造输入 (这里简单化成 [price, volume])
        std::vector<float> input_data = {
            static_cast<float>(price),
            static_cast<float>(volume)
        };
        std::vector<int64_t> input_shape = {1, 2}; // batch=1, feature=2

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

        const char* input_names[] = {"input"};
        const char* output_names[] = {"output"};

        auto output_tensors = session.Run(
            Ort::RunOptions{nullptr},
            input_names, &input_tensor, 1,
            output_names, 1
        );

        float* output_arr = output_tensors.front().GetTensorMutableData<float>();
        size_t out_len = output_tensors.front().GetTensorTypeAndShapeInfo().GetElementCount();

        // === 5. 转换为交易信号 ===
        // 这里假设输出是 [buy_score, sell_score, hold_score]
        int signal_idx = std::max_element(output_arr, output_arr + out_len) - output_arr;

        if (signal_idx == 0) {
            std::cout << "[" << ts << "] Signal = BUY @ " << price << std::endl;
            ob.add_order({next_id++, "BUY", price, 10});
        } else if (signal_idx == 1) {
            std::cout << "[" << ts << "] Signal = SELL @ " << price << std::endl;
            ob.add_order({next_id++, "SELL", price, 10});
        } else {
            std::cout << "[" << ts << "] Signal = HOLD" << std::endl;
        }

        // === 6. 打印 / 记录 OrderBook 状态 ===
        ob.print_book();

        // （可选）写到 CSV，方便 Python 可视化
        // log_file << ts << "," << price << "," << signal_idx << std::endl;
    }

    return 0;
}
