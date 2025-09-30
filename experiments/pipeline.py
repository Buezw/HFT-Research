# experiments/pipeline.py
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

from factors.engine import compute_factors
from models.base import get_all_models

@dataclass
class TrainResult:
    model_name: str
    task: str
    metrics: Dict[str, float]
    roc: Optional[Dict[str, List[float]]]
    clf: Any
    X_test: pd.DataFrame
    y_test: pd.Series
    y_pred: np.ndarray
    y_prob: Optional[np.ndarray]

def _build_midprice(df: pd.DataFrame) -> pd.DataFrame:
    """处理多种输入格式，构造 midprice 与兼容列 close。"""
    if "midprice" in df.columns:
        mid = df.copy()
    elif {"bid", "ask"}.issubset(df.columns):
        mid = df.copy()
        mid["midprice"] = (df["bid"] + df["ask"]) / 2.0
    elif {"side", "price"}.issubset(df.columns):
        buy = df[df["side"] == "BUY"].reset_index(drop=True)
        sell = df[df["side"] == "SELL"].reset_index(drop=True)
        if len(buy) != len(sell):
            raise ValueError("BUY/SELL 行数不匹配，无法对齐构造 midprice")
        mid = pd.DataFrame({"ts_ns": buy["ts_ns"].values})
        mid["midprice"] = (buy["price"].values + sell["price"].values) / 2.0
    elif "price" in df.columns:
        mid = df.rename(columns={"price": "midprice"}).copy()
    else:
        raise ValueError("无法从输入构造 midprice（缺少 bid/ask 或 side/price）")

    if "ts_ns" not in mid.columns and "timestamp" in mid.columns:
        mid = mid.rename(columns={"timestamp": "ts_ns"})

    mid["close"] = mid["midprice"]
    return mid

def _make_label(mid: pd.DataFrame, horizon: int = 1, eps: float = 0.0,
                drop_equal: bool = False) -> pd.Series:
    """未来 horizon 步收益率阈值标签；>eps 记作 1，否则 0；可选丢弃小于等于 eps 的样本。"""
    ret = mid["midprice"].pct_change(horizon).shift(-horizon)
    if drop_equal and eps > 0:
        ret = ret.where(ret.abs() > eps, np.nan)
    y = (ret > eps).astype(float)  # 先 float，后面再 dropna 再转 int
    return y

def _split_ts(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2
              ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    valid = y.notna()
    X, y = X[valid], y[valid].astype(int)
    return train_test_split(X, y, shuffle=False, test_size=test_size)

def _instantiate_model(model_name: str):
    reg = get_all_models()
    if model_name not in reg:
        raise ValueError(f"Model {model_name} not found. Available: {list(reg.keys())}")
    meta = reg[model_name]
    return meta["task"], meta["class"]()

def train_once(
    df_ticks: pd.DataFrame,
    factor_names: List[str],
    model_name: str,
    horizon: int = 1,
    eps: float = 0.0,
    drop_equal: bool = False,
    test_size: float = 0.2,
    scale: bool = True
) -> TrainResult:
    """核心训练流程：返回指标、ROC、模型与测试集产物。"""
    mid = _build_midprice(df_ticks)
    X = compute_factors(mid, factor_names).astype(float).fillna(0)

    # 丢掉近似常数因子（防止无效特征污染）
    keep = X.std() > 1e-12
    X = X.loc[:, keep]
    if X.shape[1] == 0:
        raise ValueError("没有有效因子（方差≈0），请检查 factors 实现或选择。")

    y = _make_label(mid, horizon=horizon, eps=eps, drop_equal=drop_equal)

    X_train, X_test, y_train, y_test = _split_ts(X, y, test_size=test_size)

    scaler = None
    if scale:
        scaler = StandardScaler()
        X_train = pd.DataFrame(scaler.fit_transform(X_train), index=X_train.index, columns=X_train.columns)
        X_test = pd.DataFrame(scaler.transform(X_test), index=X_test.index, columns=X_test.columns)

    task, clf = _instantiate_model(model_name)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = None
    roc = None
    metrics: Dict[str, float] = {}

    if task == "classification":
        if hasattr(clf, "predict_proba"):
            prob = clf.predict_proba(X_test)
            y_prob = prob[:, 1] if (prob.ndim == 2 and prob.shape[1] > 1) else prob.ravel()
        else:
            y_prob = y_pred

        # 退化检查（单一类别或概率常数）
        if y_test.nunique() < 2 or float(np.std(y_prob)) == 0.0:
            metrics["accuracy"] = float((y_pred == y_test).mean())
            metrics["auc"] = 0.5
            roc = {"fpr": [0.0, 1.0], "tpr": [0.0, 1.0]}
        else:
            metrics["accuracy"] = accuracy_score(y_test, y_pred)
            metrics["auc"] = roc_auc_score(y_test, y_prob)
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            roc = {"fpr": fpr.tolist(), "tpr": tpr.tolist()}
    else:  # regression
        from numpy import ravel
        y_pred = ravel(y_pred)
        metrics["mse"] = mean_squared_error(y_test, y_pred)
        metrics["r2"] = r2_score(y_test, y_pred)

    return TrainResult(
        model_name=model_name,
        task=task,
        metrics=metrics,
        roc=roc,
        clf=clf,
        X_test=X_test,
        y_test=y_test,
        y_pred=y_pred,
        y_prob=y_prob
    )

def save_artifacts(
    out_dir: str,
    res: TrainResult,
    extra_meta: Optional[Dict[str, Any]] = None,
    scaler: Optional[StandardScaler] = None
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(res.clf, os.path.join(out_dir, "model.joblib"))
    if scaler is not None:
        joblib.dump(scaler, os.path.join(out_dir, "scaler.joblib"))
    res.X_test.to_parquet(os.path.join(out_dir, "X_test.parquet"))
    pd.Series(res.y_test).to_frame("y_test").to_parquet(os.path.join(out_dir, "y_test.parquet"))
    np.save(os.path.join(out_dir, "y_pred.npy"), res.y_pred)
    if res.y_prob is not None:
        np.save(os.path.join(out_dir, "y_prob.npy"), res.y_prob)
    meta = {
        "model_name": res.model_name,
        "task": res.task,
        "metrics": res.metrics,
        "roc": res.roc
    }
    if extra_meta:
        meta.update(extra_meta)
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
