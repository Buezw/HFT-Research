# factors/price/momentum.py
import pandas as pd
from factors.base import register_factor

@register_factor(name="momentum_5", category="price", desc="5-period momentum")
def momentum_5(df: pd.DataFrame) -> pd.Series:
    return df["close"].pct_change(5)

@register_factor(name="momentum_20", category="price", desc="20-period momentum")
def momentum_20(df: pd.DataFrame) -> pd.Series:
    return df["close"].pct_change(20)
