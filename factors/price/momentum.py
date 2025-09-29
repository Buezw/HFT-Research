# factors/price/momentum.py
import pandas as pd
from factors.base import register_factor

@register_factor(
    name="momentum_5",
    category="price",
    desc="5-tick momentum",
    formula=r"Momentum_5(t) = \frac{P_t}{P_{t-5}} - 1",
    explanation="Measures the percentage price change over the past 5 ticks."
)
def momentum_5(df: pd.DataFrame) -> pd.Series:
    return df["midprice"].pct_change(5)


@register_factor(
    name="momentum_20",
    category="price",
    desc="20-tick momentum",
    formula=r"Momentum_20(t) = \frac{P_t}{P_{t-20}} - 1",
    explanation="Measures the percentage price change over the past 20 ticks."
)
def momentum_20(df: pd.DataFrame) -> pd.Series:
    return df["midprice"].pct_change(20)
