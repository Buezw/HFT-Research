#pragma once
#include "Order.h"
#include <map>
#include <queue>
#include <fstream>
#include <functional>

class OrderBook {
public:
    explicit OrderBook(const std::string& trade_log_path = "trades.csv");
    ~OrderBook();

    void add_order(Order order);
    void cancel_order(int order_id);
    void print_book() const;

private:
    // 买单簿（价格高优先）
    std::map<double, std::queue<Order>, std::greater<double>> buy_orders;
    // 卖单簿（价格低优先）
    std::map<double, std::queue<Order>, std::less<double>> sell_orders;

    std::ofstream trade_log;  // 成交日志

    long long now_ns() const; 
    void log_trade(const Order& buy_order, const Order& sell_order, int qty, double price);
    void match();
    void execute_market_order(Order order);
};
