# factors/volatility/realized_vol.py
import pandas as pd
from factors.base import register_factor

@register_factor(
    name="realized_vol_20",
    category="volatility",
    desc="20-tick realized volatility",
    formula=r"RV_{20}(t) = \sqrt{\frac{1}{20} \sum_{i=1}^{20} (r_{t-i})^2}, \quad r_t = \ln \frac{P_t}{P_{t-1}}",
    explanation="Estimates short-term volatility using the rolling standard deviation of log returns over 20 ticks."
)
def realized_vol_20(df: pd.DataFrame) -> pd.Series:
    return df["midprice"].pct_change().rolling(20).std()
