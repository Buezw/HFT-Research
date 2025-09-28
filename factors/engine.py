# factors/engine.py
import pandas as pd
from factors.base import FACTOR_REGISTRY

def compute_factors(df: pd.DataFrame, factor_list=None) -> pd.DataFrame:
    if factor_list is None:
        factor_list = list(FACTOR_REGISTRY.keys())
    out = pd.DataFrame(index=df.index)
    for name in factor_list:
        try:
            func = FACTOR_REGISTRY[name]["func"]
            out[name] = func(df)
        except Exception as e:
            print(f"[WARN] Factor {name} failed: {e}")
    return out
