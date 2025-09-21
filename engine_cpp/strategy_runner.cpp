#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <array>
#include <algorithm>
#include <onnxruntime_cxx_api.h>
#include "OrderBook.h"
#include "MarketMaker.h"

// ====== 开关：调试模式（打印/快照/市场日志）。高频仿真请置为 false ======
static constexpr bool DEBUG_MODE = false;

// ====== 内存中的结果结构 ======
struct SignalRec {
    long long ts;
    double price;
    int signal; // 0/1/2 → 请按你的模型定义映射
};
struct MyTradeRec {
    long long ts;
    std::string side; // "BUY"/"SELL"
    double price;
    int qty;
    int buy_id;
    int sell_id;
};

int main() {
    // 1) ONNX
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "HFTSim");
    Ort::SessionOptions opt;
    opt.SetIntraOpNumThreads(1);
    opt.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    Ort::Session sess(env, "py_strategy/lstm_toy.onnx", opt);
    const char* in_names[]  = {"input"};   // 按你的模型 I/O 名称修改
    const char* out_names[] = {"output"};

    // 2) 撮合引擎（debug 开关透传）
    OrderBook ob("data/trades.csv", DEBUG_MODE);
    MarketMaker mm;
    int next_id = 1;

    // 3) 读取 tick 数据（顶档事件流）
    std::ifstream fin("data/orderbook_top_ticks.csv");
    if (!fin.is_open()) {
        std::cerr << "Error: could not open data/orderbook_top_ticks.csv\n";
        return -1;
    }
    std::string header; std::getline(fin, header); // ts_ns,side,price,qty

    std::vector<SignalRec>  signals;
    std::vector<MyTradeRec> mytrades;
    signals.reserve(1<<20); // 预留，减少扩容
    mytrades.reserve(1<<20);

    std::string line;
    while (std::getline(fin, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string ts_str, side_str, price_str, qty_str;
        std::getline(ss, ts_str, ',');
        std::getline(ss, side_str, ',');
        std::getline(ss, price_str, ',');
        std::getline(ss, qty_str,  ',');

        if (ts_str.empty()||side_str.empty()||price_str.empty()||qty_str.empty()) continue;

        long long ts_ns = 0; double price=0.0; double qty=0.0;
        try { ts_ns = std::stoll(ts_str); price = std::stod(price_str); qty = std::stod(qty_str); }
        catch (...) { continue; }

        // 市场对手方：注入流动性（仅内存操作）
        mm.injectLiquidity(ob, price, qty, next_id);

        // 构造模型输入特征（示例：price, qty, side_onehot, 0）
        std::array<float,4> feat {
            (float)price,
            (float)qty,
            (side_str=="BUY")?1.0f:0.0f,
            0.0f
        };
        const int64_t shape[3] = {1,1,(int64_t)feat.size()};
        Ort::MemoryInfo mem = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        Ort::Value x = Ort::Value::CreateTensor<float>(mem, (float*)feat.data(), feat.size(), shape, 3);

        auto outs = sess.Run(Ort::RunOptions{nullptr}, in_names, &x, 1, out_names, 1);
        auto& o0 = outs.front();
        float* logits = o0.GetTensorMutableData<float>();
        size_t C = o0.GetTensorTypeAndShapeInfo().GetElementCount();
        int signal_idx = (C>0) ? int(std::max_element(logits, logits+C) - logits) : 2; // 默认为 HOLD(2)

        // 记录信号（仅内存）
        signals.push_back({ts_ns, price, signal_idx});

        if (DEBUG_MODE) {
            if (signal_idx==0) std::cout<<"["<<ts_ns<<"] BUY @ "<<price<<"\n";
            else if (signal_idx==1) std::cout<<"["<<ts_ns<<"] SELL @ "<<price<<"\n";
            else std::cout<<"["<<ts_ns<<"] HOLD\n";
        }

        // 根据信号下单（仅内存撮合）
        if (signal_idx == 0) { // BUY
            TradeResult tr = ob.add_order({next_id++, "BUY", "LIMIT", price, 10, ts_ns});
            if (tr.executed) {
                mytrades.push_back({ts_ns, "BUY", tr.price, tr.qty, tr.buy_order_id, tr.sell_order_id});
            }
        } else if (signal_idx == 1) { // SELL
            TradeResult tr = ob.add_order({next_id++, "SELL", "LIMIT", price, 10, ts_ns});
            if (tr.executed) {
                mytrades.push_back({ts_ns, "SELL", tr.price, tr.qty, tr.buy_order_id, tr.sell_order_id});
            }
        }
        // HOLD 不下单
    }
    fin.close();

    // 4) 一次性写出结果（避免运行期 I/O 阻塞）
    {
        std::ofstream f("data/signals_buy.csv", std::ios::out);
        f << "timestamp,price,signal\n";
        for (const auto& r : signals) {
            f << r.ts << "," << r.price << "," << r.signal << "\n";
        }
    }
    {
        std::ofstream f("data/trades_executed.csv", std::ios::out);
        f << "ts_ns,side,price,qty,buy_id,sell_id\n";
        for (const auto& t : mytrades) {
            f << t.ts << "," << t.side << "," << t.price << "," << t.qty
              << "," << t.buy_id << "," << t.sell_id << "\n";
        }
    }

    if (DEBUG_MODE) {
        std::cout << "[runner] signals: " << signals.size()
                  << " , my_trades: " << mytrades.size() << "\n";
    }
    return 0;
}
