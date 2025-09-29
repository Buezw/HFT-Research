# app.py
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import pandas as pd
import factors  # trigger auto-registration
from factors.base import get_all_factors
from factors.engine import compute_factors

app = FastAPI(title="HFTSim Factors Directory")

# static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/factors")
async def api_factors():
    """Return all registered factors metadata"""
    return JSONResponse(get_all_factors())


@app.get("/api/compute")
async def api_compute(factor: str = Query(...)):
    """Compute one factor and return time series"""
    df = pd.read_csv("data/orderbook_top_ticks.csv")

    # construct midprice if needed
    if "midprice" not in df.columns:
        if "bid" in df.columns and "ask" in df.columns:
            df["midprice"] = (df["bid"] + df["ask"]) / 2
        elif "price" in df.columns:  # fallback if only trade price available
            df["midprice"] = df["price"]
        else:
            raise ValueError("No suitable columns found to construct midprice")

    # compute factor
    X = compute_factors(df, [factor])

    if factor not in X.columns:
        raise ValueError(f"Factor {factor} could not be computed. Available: {X.columns.tolist()}")

    series = X[factor].fillna(0)

    return {
        "x": df.index.astype(str).tolist(),
        "y": series.tolist()
    }
