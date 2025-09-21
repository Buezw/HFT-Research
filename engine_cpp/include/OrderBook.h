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

// ===== 成交结构 =====
struct Trade {
    long long ts_ns;
    int buy_order_id;
    int sell_order_id;
    double price;
    int quantity;
};

// ===== OrderBook 类 =====
class OrderBook {
public:
    OrderBook(const std::string& trade_log_path = "trades.csv");
    ~OrderBook();

    void add_order(Order order);
    void cancel_order(int order_id);
    void print_book() const;

private:
    // 买卖盘 (price → 队列)
    std::map<double, std::queue<Order>, std::greater<double>> buy_orders; // 买盘 (降序)
    std::map<double, std::queue<Order>, std::less<double>> sell_orders;   // 卖盘 (升序)

    std::vector<Trade> trades;   // 最近成交记录
    std::ofstream trade_log;     // 成交流水文件
    mutable std::ofstream snapshot_log;  // 允许在 const 方法里写
  // 盘口快照文件

    long long now_ns() const;
    void match();
    void execute_market_order(Order order);
    void log_trade(const Order& buy_order, const Order& sell_order, int qty, double price);
};
