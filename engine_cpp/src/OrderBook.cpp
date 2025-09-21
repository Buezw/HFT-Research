#include "OrderBook.h"
#include <iostream>
#include <algorithm>
#include <chrono>

// ===== 工具函数：获取当前时间（纳秒级 Unix 时间戳） =====
long long OrderBook::now_ns() const {
    auto now = std::chrono::system_clock::now().time_since_epoch();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
}

// ===== 构造 & 析构 =====
OrderBook::OrderBook(const std::string& trade_log_path, bool debug) : debug_mode(debug) {
    if (debug_mode) {
        trade_log.open(trade_log_path, std::ios::out);
        if (trade_log.is_open()) {
            trade_log << "ts_ns,buy_id,sell_id,price,qty\n";
        }
        snapshot_log.open("orderbook_snapshot.csv", std::ios::out);
        if (snapshot_log.is_open()) {
            snapshot_log << "ts_ns,side,price,qty\n";
        }
    }
}

OrderBook::~OrderBook() {
    if (trade_log.is_open())    trade_log.close();
    if (snapshot_log.is_open()) snapshot_log.close();
}

// ===== 下单入口（返回最近一次撮合结果）=====
TradeResult OrderBook::add_order(Order order) {
    if (order.ts_ns == 0) {
        order.ts_ns = now_ns();
    }

    TradeResult result;

    if (order.type == "MARKET") {
        result = execute_market_order(order);
    } else { // LIMIT
        if (order.side == "BUY") {
            buy_orders[order.price].push(order);
        } else {
            sell_orders[order.price].push(order);
        }
        result = match();
    }

    // 仅调试时打印盘口
    print_book();
    return result;
}

// ===== 撤单 =====
void OrderBook::cancel_order(int order_id) {
    bool found = false;

    // 买单簿
    for (auto it = buy_orders.begin(); it != buy_orders.end();) {
        std::queue<Order> new_q;
        while (!it->second.empty()) {
            Order o = it->second.front(); it->second.pop();
            if (o.id == order_id) {
                if (debug_mode) {
                    std::cout << "CANCEL: BUY#" << o.id 
                              << " @ " << o.price << " x " << o.qty << "\n";
                }
                found = true;
            } else {
                new_q.push(o);
            }
        }
        if (new_q.empty()) it = buy_orders.erase(it);
        else { it->second = std::move(new_q); ++it; }
    }

    // 卖单簿
    for (auto it = sell_orders.begin(); it != sell_orders.end();) {
        std::queue<Order> new_q;
        while (!it->second.empty()) {
            Order o = it->second.front(); it->second.pop();
            if (o.id == order_id) {
                if (debug_mode) {
                    std::cout << "CANCEL: SELL#" << o.id 
                              << " @ " << o.price << " x " << o.qty << "\n";
                }
                found = true;
            } else {
                new_q.push(o);
            }
        }
        if (new_q.empty()) it = sell_orders.erase(it);
        else { it->second = std::move(new_q); ++it; }
    }

    if (debug_mode && !found) {
        std::cout << "Order ID " << order_id << " not found.\n";
    }
    print_book();
}

// ===== 打印盘口 & 写快照（仅 debug 模式）=====
void OrderBook::print_book() const {
    if (!debug_mode) return;

    long long ts = now_ns();

    std::cout << "\n--- Order Book Snapshot ---\n";

    std::cout << "BUY side:\n";
    for (const auto& [price, q] : buy_orders) {
        int total_qty = 0;
        std::queue<Order> tmp = q;
        while (!tmp.empty()) { total_qty += tmp.front().qty; tmp.pop(); }
        std::cout << "  " << price << " x " << total_qty << "\n";

        if (snapshot_log.is_open()) {
            snapshot_log << ts << ",BUY," << price << "," << total_qty << "\n";
        }
    }

    std::cout << "SELL side:\n";
    for (const auto& [price, q] : sell_orders) {
        int total_qty = 0;
        std::queue<Order> tmp = q;
        while (!tmp.empty()) { total_qty += tmp.front().qty; tmp.pop(); }
        std::cout << "  " << price << " x " << total_qty << "\n";

        if (snapshot_log.is_open()) {
            snapshot_log << ts << ",SELL," << price << "," << total_qty << "\n";
        }
    }

    std::cout << "----------------------------\n";
}

// ===== 成交日志（仅 debug 模式写文件，但总是 push 到内存）=====
void OrderBook::log_trade(const Order& buy_order, const Order& sell_order, int qty, double price) {
    const long long ts = now_ns();

    if (trade_log.is_open()) {
        trade_log << ts << ","
                  << buy_order.id << ","
                  << sell_order.id << ","
                  << price << ","
                  << qty << "\n";
    }

    trades.push_back({ts, buy_order.id, sell_order.id, price, qty});

    if (debug_mode) {
        std::cout << "TRADE: " << qty
                  << " @ " << price
                  << " between BUY#" << buy_order.id
                  << " and SELL#" << sell_order.id << "\n";
    }
}

// ===== 限价撮合（返回最近一次成交）=====
TradeResult OrderBook::match() {
    TradeResult result;
    while (!buy_orders.empty() && !sell_orders.empty()) {
        auto best_buy_it  = buy_orders.begin();
        auto best_sell_it = sell_orders.begin();
        double buy_price  = best_buy_it->first;
        double sell_price = best_sell_it->first;

        if (buy_price >= sell_price) {
            Order buy_order  = best_buy_it->second.front();
            Order sell_order = best_sell_it->second.front();

            const int trade_qty = std::min(buy_order.qty, sell_order.qty);
            log_trade(buy_order, sell_order, trade_qty, sell_price);

            result = {true, sell_price, trade_qty, buy_order.id, sell_order.id};

            // 扣减并维护队列
            buy_order.qty  -= trade_qty;
            sell_order.qty -= trade_qty;

            best_buy_it->second.pop();
            if (buy_order.qty > 0) best_buy_it->second.push(buy_order);
            if (best_buy_it->second.empty()) buy_orders.erase(best_buy_it);

            best_sell_it->second.pop();
            if (sell_order.qty > 0) best_sell_it->second.push(sell_order);
            if (best_sell_it->second.empty()) sell_orders.erase(best_sell_it);
        } else {
            break;
        }
    }
    return result;
}

// ===== 市价撮合（返回最近一次成交）=====
TradeResult OrderBook::execute_market_order(Order order) {
    TradeResult result;

    if (order.side == "BUY") {
        while (order.qty > 0 && !sell_orders.empty()) {
            auto best_sell_it = sell_orders.begin();
            Order sell_order  = best_sell_it->second.front();

            const int trade_qty = std::min(order.qty, sell_order.qty);
            log_trade(order, sell_order, trade_qty, sell_order.price);

            result = {true, sell_order.price, trade_qty, order.id, sell_order.id};

            order.qty      -= trade_qty;
            sell_order.qty -= trade_qty;

            best_sell_it->second.pop();
            if (sell_order.qty > 0) best_sell_it->second.push(sell_order);
            if (best_sell_it->second.empty()) sell_orders.erase(best_sell_it);
        }
    } else { // MARKET SELL
        while (order.qty > 0 && !buy_orders.empty()) {
            auto best_buy_it = buy_orders.begin();
            Order buy_order  = best_buy_it->second.front();

            const int trade_qty = std::min(order.qty, buy_order.qty);
            log_trade(buy_order, order, trade_qty, buy_order.price);

            result = {true, buy_order.price, trade_qty, buy_order.id, order.id};

            order.qty     -= trade_qty;
            buy_order.qty -= trade_qty;

            best_buy_it->second.pop();
            if (buy_order.qty > 0) best_buy_it->second.push(buy_order);
            if (best_buy_it->second.empty()) buy_orders.erase(best_buy_it);
        }
    }

    if (debug_mode && order.qty > 0) {
        std::cout << "MARKET order unfilled qty: " << order.qty << " discarded.\n";
    }

    return result;
}
