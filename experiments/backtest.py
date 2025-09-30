# experiments/backtest.py
# backtest CLI: read artifacts, compute signals & diagnostics, output JSON
import argparse, os, json, sys
from typing import Optional

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import (
    precision_recall_curve, average_precision_score,
    confusion_matrix, brier_score_loss
)
from sklearn.calibration import calibration_curve

# only reused inside experiments (keep FastAPI clean)
from experiments.pipeline import _build_midprice


def run_backtest(artdir: str, data_path: str, horizon: int, json_path: Optional[str]) -> dict:
    # ---- load artifacts
    model_path = os.path.join(artdir, "model.joblib")
    x_test_path = os.path.join(artdir, "X_test.parquet")
    y_test_path = os.path.join(artdir, "y_test.parquet")
    if not (os.path.exists(model_path) and os.path.exists(x_test_path) and os.path.exists(y_test_path)):
        raise FileNotFoundError(
            "Artifacts incomplete. Expect model.joblib, X_test.parquet, y_test.parquet in " + artdir
        )

    clf = joblib.load(model_path)
    try:
        X_test = pd.read_parquet(x_test_path)   # requires pyarrow or fastparquet
        y_test = pd.read_parquet(y_test_path)["y_test"].to_numpy()
    except Exception as e:
        raise RuntimeError("Failed to read parquet. Install pyarrow: pip install pyarrow. Detail: %s" % e)

    # ---- build test returns aligned with label horizon
    df = pd.read_csv(data_path)
    mid = _build_midprice(df)
    ret_full = mid["midprice"].pct_change(horizon).shift(-horizon)
    ret_test = ret_full.loc[X_test.index].fillna(0.0).to_numpy()

    # ---- predictions
    y_prob = None
    if hasattr(clf, "predict_proba"):
        prob = clf.predict_proba(X_test)
        y_prob = prob[:, 1] if (prob.ndim == 2 and prob.shape[1] > 1) else prob.ravel()
    y_pred = clf.predict(X_test)

    # ---- threshold (best F1 on test for demo; production should use validation!)
    if (y_prob is not None) and (float(np.std(y_prob)) > 0.0):
        prec, rec, thr = precision_recall_curve(y_test, y_prob)
        if len(thr) > 0:
            f1 = 2 * prec * rec / (prec + rec + 1e-12)
            idx = int(np.nanargmax(f1[:-1])) if len(f1) > 1 else 0
            threshold = float(thr[idx])
        else:
            threshold = 0.5
        signals = (y_prob > threshold).astype(int)
    else:
        threshold = 0.5
        signals = y_pred.astype(int)

    # ---- PnL & risk
    step_pnl = signals * ret_test
    cum = np.cumsum(step_pnl)
    peak = np.maximum.accumulate(cum)
    drawdown = cum - peak
    max_drawdown = float(drawdown.min() if len(drawdown) else 0.0)
    sharpe_step = float(step_pnl.mean() / (step_pnl.std() + 1e-12))
    exposure = float(np.mean(signals))
    turnover = float(np.sum(np.abs(np.diff(signals))))  # entry/exit count for 0/1 signal

    # ---- classification at chosen threshold
    if len(np.unique(y_test)) == 2:
        tn, fp, fn, tp = confusion_matrix(y_test, signals).ravel()
    else:
        tn = fp = fn = tp = 0
    precision_th = float(tp / (tp + fp + 1e-12))
    recall_th = float(tp / (tp + fn + 1e-12))
    f1_th = float(2 * precision_th * recall_th / (precision_th + recall_th + 1e-12))

    # ---- PR & calibration (if proba exists)
    pr_curve = None
    ap = None
    calib = None
    brier = None
    if (y_prob is not None) and (float(np.std(y_prob)) > 0.0):
        prec, rec, _thr = precision_recall_curve(y_test, y_prob)
        ap = float(average_precision_score(y_test, y_prob))
        pr_curve = {"precision": prec.tolist(), "recall": rec.tolist()}
        frac_pos, mean_pred = calibration_curve(y_test, y_prob, n_bins=10, strategy="quantile")
        calib = {"mean_pred": mean_pred.tolist(), "frac_pos": frac_pos.tolist()}
        brier = float(brier_score_loss(y_test, y_prob))

    # ---- return distribution (clipped tails for readability)
    if len(ret_test) > 10:
        lo, hi = np.percentile(ret_test, [1, 99])
    else:
        lo, hi = (float(np.min(ret_test)) if len(ret_test) else 0.0,
                  float(np.max(ret_test)) if len(ret_test) else 0.0)
    bins = np.linspace(lo, hi, 31) if hi > lo else np.linspace(-1e-6, 1e-6, 31)
    hist_counts, hist_edges = np.histogram(ret_test, bins=bins)

    # ---- time axis
    if "ts_ns" in mid.columns:
        ts = mid.loc[X_test.index, "ts_ns"].astype(str).tolist()
    else:
        ts = list(map(str, range(len(cum))))

    payload = {
        "threshold": threshold,
        "series": {
            "ts": ts,
            "ret": ret_test.tolist(),
            "signals": signals.tolist(),
            "pnl": cum.tolist(),           # cumulative PnL
            "step_pnl": step_pnl.tolist(),
            "drawdown": drawdown.tolist(),
            "y_test": y_test.tolist(),
            "y_prob": (y_prob.tolist() if y_prob is not None else None),
        },
        "risk": {
            "max_drawdown": max_drawdown,
            "sharpe_step": sharpe_step,
            "exposure": exposure,
            "turnover": turnover
        },
        "classification": {
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
            "precision_at_threshold": precision_th,
            "recall_at_threshold": recall_th,
            "f1_at_threshold": f1_th,
            "average_precision": ap,
            "brier": brier,
        },
        "curves": {
            "pr": pr_curve,
            "calibration": calib,
        },
        "ret_hist": {
            "edges": hist_edges.tolist(),
            "counts": hist_counts.tolist()
        }
    }

    if json_path:
        with open(json_path, "w") as f:
            json.dump(payload, f)
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artdir", default="artifacts/latest")
    ap.add_argument("--data", default="data/orderbook_top_ticks.csv")
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--json", default="", help="If set, write result JSON to this path")
    args = ap.parse_args()

    try:
        payload = run_backtest(
            artdir=args.artdir, data_path=args.data, horizon=args.horizon,
            json_path=(args.json if args.json else None)
        )
        if not args.json:
            print(json.dumps(payload))
    except Exception as e:
        sys.stderr.write(f"[backtest error] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
