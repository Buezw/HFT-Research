# app.py
# FastAPI server for HFTSim (API only calls CLIs; no training logic here)

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
import sys
import json
import time
import subprocess
import pandas as pd

# Trigger auto-registration for factors/models (metadata only; no training here)
import factors
import models
from factors.base import get_all_factors
from factors.engine import compute_factors
from models.base import get_all_models

# -----------------------------------------------------------------------------
# FastAPI app & static/templates
# -----------------------------------------------------------------------------
# app.py
from pathlib import Path
from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent

app = FastAPI(title="HFTSim Factors & Models")

# 不再使用 /static
# app.mount("/static", StaticFiles(directory="static"), name="static")

# 改为直接暴露 templates 下面的 css/js
app.mount("/js",  StaticFiles(directory=str(BASE_DIR / "templates" / "js")),  name="js")
app.mount("/css", StaticFiles(directory=str(BASE_DIR / "templates" / "css")), name="css")

# 模板目录（保持不变）
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _run(cmd: list[str]) -> str:
    """
    Run a subprocess command and return stdout. Raise HTTPException on failure.
    """
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn process: {e}")

    if p.returncode != 0:
        err = (p.stderr or "").strip()
        out = (p.stdout or "").strip()
        msg = err if err else out if out else "subprocess failed"
        raise HTTPException(status_code=500, detail=msg)

    return (p.stdout or "").strip()


def _mk_outdir(model: str, factor: str, horizon: int, eps: float) -> str:
    """
    Make a unique artifacts directory name like:
    artifacts/20250101-120000_logit_mom5-mom20_h5_e0.0
    """
    ts = time.strftime("%Y%m%d-%H%M%S")
    tag = f"{model}_{factor.replace(',', '-').replace(' ', '')}_h{horizon}_e{eps}"
    outdir = os.path.join("artifacts", f"{ts}_{tag}")
    os.makedirs(outdir, exist_ok=True)
    return outdir


def _ensure_midprice(df: pd.DataFrame) -> pd.DataFrame:
    """Construct midprice if needed (used by /api/compute)."""
    if "midprice" in df.columns:
        return df
    if {"bid", "ask"}.issubset(df.columns):
        df = df.copy()
        df["midprice"] = (df["bid"] + df["ask"]) / 2.0
        return df
    if {"side", "price"}.issubset(df.columns):
        buy = df[df["side"] == "BUY"].reset_index(drop=True)
        sell = df[df["side"] == "SELL"].reset_index(drop=True)
        if len(buy) != len(sell):
            raise HTTPException(status_code=400, detail="BUY/SELL row count mismatch; cannot build midprice")
        out = pd.DataFrame({"ts_ns": buy["ts_ns"].values})
        out["midprice"] = (buy["price"].values + sell["price"].values) / 2.0
        return out
    if "price" in df.columns:
        df = df.copy()
        df["midprice"] = df["price"]
        return df
    raise HTTPException(status_code=400, detail="No suitable columns to construct midprice")


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/factors")
async def api_factors():
    """
    Return all registered factors grouped by category.
    """
    all_factors = get_all_factors()
    grouped = {}
    for name, meta in all_factors.items():
        cat = meta.get("category", "Uncategorized")
        if cat not in grouped:
            grouped[cat] = {}
        grouped[cat][name] = meta
    return JSONResponse(grouped)


@app.get("/api/models")
async def api_models():
    """
    Return all registered models metadata (JSON-safe; class objects omitted).
    """
    all_models = get_all_models()
    safe = {}
    for name, meta in all_models.items():
        safe[name] = {
            "name": meta.get("name", name),
            "desc": meta.get("desc", ""),
            "task": meta.get("task", "classification")
        }
    return JSONResponse(safe)


@app.get("/api/compute")
async def api_compute(
    factor: str = Query(..., description="Single factor name"),
    data_path: str = Query("data/orderbook_top_ticks.csv", description="CSV path")
):
    """
    Compute one factor's time series and return {x, y}.
    """
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {e}")

    df = _ensure_midprice(df)

    try:
        X = compute_factors(df, [factor])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Factor compute failed: {e}")

    if factor not in X.columns:
        raise HTTPException(status_code=400, detail=f"Factor {factor} not computed")

    series = X[factor].fillna(0)
    # x 轴优先 ts_ns，否则用 index
    if "ts_ns" in df.columns:
        x = df.loc[series.index, "ts_ns"].astype(str).tolist()
    else:
        x = series.index.astype(str).tolist()

    return {"x": x, "y": series.tolist()}


@app.get("/api/train")
async def api_train(
    factor: str = Query(..., description="Comma-separated factor names"),
    model: str = Query(...),
    horizon: int = Query(5),
    eps: float = Query(0.0),
    drop_equal: bool = Query(False),
    scale: bool = Query(True),
    data_path: str = Query("data/orderbook_top_ticks.csv"),
):
    """
    API only *calls* the CLI trainer (experiments/train.py).
    Uses fixed 5:1 split => test_size = 1/6.
    Returns meta.json + artifacts_dir.
    """
    outdir = _mk_outdir(model, factor, horizon, eps)

    cmd = [
        sys.executable, "-m", "experiments.train",
        "--data", data_path,
        "--model", model,
        "--factors", factor,
        "--horizon", str(horizon),
        "--eps", str(eps),
        "--test_size", str(1.0 / 6.0),  # 5:1 split
        "--outdir", outdir,
    ]
    if drop_equal:
        cmd.append("--drop_equal")
    if scale:
        cmd.append("--scale")

    _ = _run(cmd)

    meta_path = os.path.join(outdir, "meta.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=500, detail="meta.json not found after training")

    try:
        with open(meta_path, "r") as f:
            meta = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read meta.json: {e}")

    meta["artifacts_dir"] = outdir
    return JSONResponse(meta)


@app.get("/api/backtest")
async def api_backtest(
    artifacts_dir: str = Query(
        None,
        description="Use the artifacts_dir returned by /api/train. "
                    "If omitted, this route will first call /api/train."
    ),
    factor: str = Query(None, description="Required if artifacts_dir is omitted"),
    model: str = Query(None, description="Required if artifacts_dir is omitted"),
    horizon: int = Query(5),
    data_path: str = Query("data/orderbook_top_ticks.csv"),
):
    """
    API only *calls* the CLI backtester (experiments/backtest.py).
    If artifacts_dir is not provided, it will call /api/train first (with same horizon).
    Returns {threshold, series{ts,ret,signals,pnl,y_test,y_prob}, artifacts_dir}.
    """
    # If no artifacts_dir, train once to produce artifacts
    if not artifacts_dir:
        if not (factor and model):
            raise HTTPException(status_code=400, detail="Missing artifacts_dir; provide factor & model to train first")
        # Call our own /api/train to produce artifacts_dir (fixed 5:1 inside)
        train_meta = await api_train(
            factor=factor,
            model=model,
            horizon=horizon,
            eps=0.0,
            drop_equal=False,
            scale=True,
            data_path=data_path,
        )
        # train_meta is a JSONResponse; extract body
        train_meta_body = json.loads(train_meta.body.decode()) if hasattr(train_meta, "body") else train_meta
        artifacts_dir = train_meta_body["artifacts_dir"]

    # Run backtest CLI and write JSON to artifacts_dir/backtest.json
    backtest_json = os.path.join(artifacts_dir, "backtest.json")
    cmd = [
        sys.executable, "-m", "experiments.backtest",
        "--artdir", artifacts_dir,
        "--data", data_path,
        "--horizon", str(horizon),
        "--json", backtest_json,
    ]
    _ = _run(cmd)

    if not os.path.exists(backtest_json):
        raise HTTPException(status_code=500, detail="backtest.json not found after backtest")

    try        :
        with open(backtest_json, "r") as f:
            payload = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read backtest.json: {e}")

    payload["artifacts_dir"] = artifacts_dir
    return JSONResponse(payload)
