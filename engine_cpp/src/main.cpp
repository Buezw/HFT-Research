#include <iostream>
#include <map>
#include <queue>
#include <string>

// 订单结构
struct Order {
    int id;
    std::string side;  // "BUY" or "SELL"
    double price;
    int qty;
};

// 简单订单簿：买单用 price 从高到低排，卖单用 price 从低到高排
class OrderBook {
public:
    void add_order(const Order& order) {
        if (order.side == "BUY") {
            buy_orders[order.price].push(order);
        } else {
            sell_orders[order.price].push(order);
        }
        match();
    }

private:
    // 买单簿：价格高优先
    std::map<double, std::queue<Order>, std::greater<double>> buy_orders;
    // 卖单簿：价格低优先
    std::map<double, std::queue<Order>, std::less<double>> sell_orders;

    void match() {
        while (!buy_orders.empty() && !sell_orders.empty()) {
            auto best_buy_it = buy_orders.begin();
            auto best_sell_it = sell_orders.begin();

            double buy_price = best_buy_it->first;
            double sell_price = best_sell_it->first;

            if (buy_price >= sell_price) {
                // 撮合成交
                Order buy_order = best_buy_it->second.front();
                Order sell_order = best_sell_it->second.front();

                int trade_qty = std::min(buy_order.qty, sell_order.qty);
                std::cout << "TRADE: " << trade_qty
                          << " @ " << sell_price
                          << " between BUY#" << buy_order.id
                          << " and SELL#" << sell_order.id << std::endl;

                // 更新剩余数量
                buy_order.qty -= trade_qty;
                sell_order.qty -= trade_qty;

                // 更新买单队列
                best_buy_it->second.pop();
                if (buy_order.qty > 0) {
                    best_buy_it->second.push(buy_order);
                }
                if (best_buy_it->second.empty()) {
                    buy_orders.erase(best_buy_it);
                }

                // 更新卖单队列
                best_sell_it->second.pop();
                if (sell_order.qty > 0) {
                    best_sell_it->second.push(sell_order);
                }
                if (best_sell_it->second.empty()) {
                    sell_orders.erase(best_sell_it);
                }

            } else {
                break; // 无法成交
            }
        }
    }
};

// 主函数：演示
int main() {
    OrderBook ob;
    ob.add_order({1, "BUY", 101.0, 10});
    ob.add_order({2, "SELL", 100.5, 5});
    ob.add_order({3, "SELL", 101.0, 7});
    ob.add_order({4, "BUY", 99.0, 3});

    return 0;
}
