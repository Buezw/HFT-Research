# factors/liquidity/spread.py
import pandas as pd
from factors.base import register_factor

@register_factor(
    name="spread",
    category="liquidity",
    desc="Bid-ask spread",
    formula=r"Spread(t) = Ask_1(t) - Bid_1(t)",
    explanation="The price difference between the best ask and best bid, reflecting market liquidity."
)
def spread(df: pd.DataFrame) -> pd.Series:
    return df["ask"] - df["bid"]


@register_factor(
    name="order_imbalance",
    category="liquidity",
    desc="Order book imbalance",
    formula=r"OI(t) = \frac{Q_{bid}(t) - Q_{ask}(t)}{Q_{bid}(t) + Q_{ask}(t)}",
    explanation="Measures the imbalance between bid and ask order quantities, indicating buy/sell pressure."
)
def order_imbalance(df: pd.DataFrame) -> pd.Series:
    denom = (df["bid_qty"] + df["ask_qty"]).replace(0, pd.NA)
    return (df["bid_qty"] - df["ask_qty"]) / denom
