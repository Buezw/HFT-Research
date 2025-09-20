#include "OrderBook.h"

int main() {
    OrderBook ob("trades.csv");

    // 限价单（系统会自动加时间戳）
    ob.add_order({1, "BUY", 101.0, 10});
    ob.add_order({2, "SELL", 100.5, 5});
    ob.add_order({3, "SELL", 101.0, 7});

    // 市价单
    ob.add_order({4, "BUY", 0.0, 8, "MARKET"});
    ob.add_order({5, "SELL", 0.0, 12, "MARKET"});

    return 0;
}
