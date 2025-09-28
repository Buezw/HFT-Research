# factors/liquidity/order_imbalance.py
import pandas as pd
from factors.base import register_factor

@register_factor(name="order_imbalance", category="liquidity", desc="Bid-Ask volume imbalance")
def order_imbalance(df: pd.DataFrame) -> pd.Series:
    return (df["bid_vol"] - df["ask_vol"]) / (df["bid_vol"] + df["ask_vol"] + 1e-9)
