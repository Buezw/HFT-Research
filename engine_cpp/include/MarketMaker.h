#pragma once
#include "OrderBook.h"

class MarketMaker {
public:
    // 向订单簿注入双边流动性
    void injectLiquidity(OrderBook& ob, double mid_price, double market_size, int& next_id) {
        // 挂买单
        ob.add_order({next_id++, "BUY", "LIMIT", mid_price - 0.01, static_cast<int>(market_size)});
        // 挂卖单
        ob.add_order({next_id++, "SELL", "LIMIT", mid_price + 0.01, static_cast<int>(market_size)});
    }
};
