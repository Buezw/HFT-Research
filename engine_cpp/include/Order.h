#pragma once
#include <string>

struct Order {
    int id;
    std::string side;   // "BUY" or "SELL"
    double price;       // 市价单可忽略
    int qty;
    std::string type = "LIMIT"; // "LIMIT" or "MARKET"
    long long ts_ns = 0;        // 纳秒级时间戳
};
