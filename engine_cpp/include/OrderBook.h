#pragma once
#include <map>
#include <queue>
#include <string>
#include <fstream>
#include <vector>

// ===== 订单结构 =====
struct Order {
    int id;
    std::string side;   // "BUY" / "SELL"
    std::string type;   // "LIMIT" / "MARKET"
    double price;
    int qty;
    long long ts_ns = 0; // 纳秒级时间戳
};

// ===== 成交结构（市场视角快照用）=====
struct Trade {
    long long ts_ns;
    int buy_order_id;
    int sell_order_id;
    double price;
    int quantity;
};

// ===== 返回给上层的单次撮合结果（你的策略视角）=====
struct TradeResult {
    bool executed = false;  // 是否有成交
    double price = 0.0;     // 成交价
    int qty = 0;            // 成交数量
    int buy_order_id = -1;
    int sell_order_id = -1;
};

// ===== OrderBook =====
class OrderBook {
public:
    // debug=false 时：不打印、不写快照、不写 trades.csv（避免阻塞）
    explicit OrderBook(const std::string& trade_log_path = "trades.csv", bool debug = false);
    ~OrderBook();

    TradeResult add_order(Order order);   // 下单（支持 LIMIT / MARKET），返回最近一次撮合结果
    void cancel_order(int order_id);
    void print_book() const;              // debug=false 时直接 return

private:
    bool debug_mode = false;

    // 买卖盘 (price → 队列)
    std::map<double, std::queue<Order>, std::greater<double>> buy_orders; // 买盘 (降序)
    std::map<double, std::queue<Order>, std::less<double>>    sell_orders; // 卖盘 (升序)

    // 内部保存的市场成交（内存）
    std::vector<Trade> trades;

    // 仅在 debug=true 时开启的日志文件（避免阻塞）
    std::ofstream trade_log;              // 成交流水文件（市场视角）
    mutable std::ofstream snapshot_log;   // 盘口快照文件

    long long now_ns() const;

    TradeResult match();                       // 限价撮合（返回最近一次成交）
    TradeResult execute_market_order(Order);   // 市价撮合（返回最近一次成交）
    void log_trade(const Order& buy_order, const Order& sell_order, int qty, double price);
};
