# dashboard_review.py
import os
import math
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="HFTSim – Industrial Review", layout="wide")
st.title("🏦 HFTSim – Strategy Review Dashboard")

# -------------------------------
# 1) 文件路径
# -------------------------------
SIGNAL_FILE = "data/signals_buy.csv"          # timestamp,price,signal(0/1/2)
TRADE_FILE  = "data/trades_executed.csv"      # ts_ns,side,price,qty,buy_id,sell_id

# -------------------------------
# 2) 读数据 + 预处理
# -------------------------------
@st.cache_data(show_spinner=False)
def load_signals(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=["timestamp","price","signal"])
    df = pd.read_csv(path)
    # 允许 ns 时间戳或标准时间字符串
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    # 过滤坏时间
    df = df[df["timestamp"].notna()].sort_values("timestamp")
    # 映射信号文本（非必需，仅备用）
    mapping = {0:"BUY", 1:"SELL", 2:"HOLD"}
    if "signal" in df.columns:
        df["signal_txt"] = df["signal"].map(mapping).fillna(df["signal"].astype(str))
    else:
        df["signal_txt"] = "NA"
    # 去重
    df = df.drop_duplicates(subset=["timestamp"])
    return df.reset_index(drop=True)

@st.cache_data(show_spinner=False)
def load_trades(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        cols = ["ts_ns","side","price","qty","buy_id","sell_id"]
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path)
    # 成交时间可能是 ns 时间戳或字符串
    # 如果是大整数，pd.to_datetime可以识别 ns；若失败，errors='coerce'
    df["ts_ns"] = pd.to_datetime(df["ts_ns"], errors="coerce")
    df = df[df["ts_ns"].notna()].sort_values("ts_ns")
    # 方向规范化
    if "side" in df.columns:
        df["side"] = df["side"].str.upper().str.strip()
    else:
        df["side"] = "UNKNOWN"
    # 数值
    for c in ["price","qty"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["price","qty"])
    return df.reset_index(drop=True)

df_sig  = load_signals(SIGNAL_FILE)
df_trd  = load_trades(TRADE_FILE)

if df_trd.empty:
    st.warning("没有发现成交数据（data/trades_executed.csv）。先跑完模拟再来复盘。")
    st.stop()

# -------------------------------
# 3) 自动选择聚合粒度 + 控件
# -------------------------------
t0 = df_trd["ts_ns"].min()
t1 = df_trd["ts_ns"].max()
span_sec = (t1 - t0).total_seconds() if pd.notna(t0) and pd.notna(t1) else 0.0

# 按跨度自动给一个合理粒度
def auto_bucket(seconds: float) -> str:
    if seconds <= 2.0:
        return "10ms"
    if seconds <= 60.0:
        return "100ms"
    if seconds <= 3600.0:
        return "1s"
    return "1min"

default_bucket = auto_bucket(span_sec)
with st.sidebar:
    st.header("⚙️ 设置")
    st.write(f"数据跨度约：**{span_sec:.3f} 秒**")
    bucket = st.selectbox("聚合粒度", ["10ms","100ms","1s","1min"], index=["10ms","100ms","1s","1min"].index(default_bucket))
    show_tables = st.checkbox("显示明细表（可能较慢）", value=False)

# -------------------------------
# 4) 标的价格基准（用于持仓估值/滑点参考）
#    用 signals 的 price 作为 mid（不完美，但够复盘）
# -------------------------------
if df_sig.empty:
    # 万一没有signals，用成交加权均价代理价格时间线
    ref = df_trd[["ts_ns","price","qty"]].copy()
    ref = ref.rename(columns={"ts_ns":"ts"})
    # 以成交时间为锚点构造价格曲线
    ref = ref.set_index("ts").groupby(pd.Grouper(freq=bucket)).apply(lambda x: np.average(x["price"], weights=x["qty"]) if x["qty"].sum()>0 else x["price"].mean()).to_frame("mid")
else:
    ref = df_sig[["timestamp","price"]].rename(columns={"timestamp":"ts","price":"mid"}).copy()
    ref = ref.set_index("ts").sort_index()
    # 先按较细频率重采样再前向填充
    ref = ref.resample(bucket).last().ffill()

ref = ref.reset_index().rename(columns={"index":"ts"})
ref = ref.dropna(subset=["ts","mid"])

# -------------------------------
# 5) 构建持仓与PnL（仓位法：现金+持仓*mid）
# -------------------------------
# 将成交按聚合粒度对齐
trd = df_trd.copy()
trd["bucket_ts"] = trd["ts_ns"].dt.floor(bucket)

# 方向：BUY 正，SELL 负
trd["signed_qty"] = np.where(trd["side"]=="BUY", trd["qty"], np.where(trd["side"]=="SELL", -trd["qty"], 0))
trd["cash_flow"]  = - trd["price"] * trd["signed_qty"]   # 买入现金流为负，卖出为正

# 聚合（每个时间桶）
agg = trd.groupby("bucket_ts").agg(
    net_qty=("signed_qty","sum"),
    cash_delta=("cash_flow","sum"),
    vol=("qty","sum"),
    avg_price=("price","mean"),
).reset_index().rename(columns={"bucket_ts":"ts"})

# 和参考价格时间线合并
timeline = pd.merge(ref, agg, on="ts", how="outer").sort_values("ts")
timeline[["net_qty","cash_delta","vol","avg_price"]] = timeline[["net_qty","cash_delta","vol","avg_price"]].fillna(0)

# 递推：持仓 & 现金 & 账户净值
timeline["position"] = timeline["net_qty"].cumsum()
timeline["cash"]     = timeline["cash_delta"].cumsum()
timeline["equity"]   = timeline["cash"] + timeline["position"] * timeline["mid"]

# per-bucket收益（Δequity）
timeline["pnl_step"] = timeline["equity"].diff().fillna(0)
timeline["cum_pnl"]  = timeline["equity"] - timeline["equity"].iloc[0]

# -------------------------------
# 6) 关键指标
# -------------------------------
def max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    peak = series.cummax()
    dd = (series - peak)
    return dd.min()

def sharpe_from_steps(steps: pd.Series, seconds_per_bucket: float) -> float:
    # 简化计算：Sharpe = mean(step)/std(step) * sqrt(年化步数)
    # 年化系数：一年秒数约 31_536_000
    if steps.std(ddof=1) == 0:
        return 0.0
    ann_factor = math.sqrt(31_536_000 / seconds_per_bucket) if seconds_per_bucket>0 else 0
    return steps.mean() / steps.std(ddof=1) * ann_factor

# 估计每个bucket的秒数
bucket_sec = {"10ms":0.01, "100ms":0.1, "1s":1.0, "1min":60.0}[bucket]

final_pnl   = float(timeline["cum_pnl"].iloc[-1]) if len(timeline)>0 else 0.0
mdd         = float(max_drawdown(timeline["cum_pnl"]))
sharpe      = float(sharpe_from_steps(timeline["pnl_step"], bucket_sec))
turnover    = float(trd["qty"].sum() / (timeline["position"].abs().mean() + 1e-9))  # 粗略换手率
hit_rate    = float((timeline["pnl_step"]>0).mean()) if len(timeline)>0 else 0.0

# 滑点估计：成交价 vs 同桶参考价
# 将成交与 ref 按最近桶对齐，计算 (trade_price - mid) * side_sign
slip = pd.merge(
    trd[["ts_ns","bucket_ts","side","price","qty","signed_qty"]],
    ref.rename(columns={"ts":"bucket_ts"}),
    on="bucket_ts", how="left"
)
slip["side_sign"] = np.where(slip["signed_qty"]>=0, 1, -1)  # BUY正 SELL负
slip["slippage"]  = (slip["price"] - slip["mid"]) * slip["side_sign"]

avg_slip   = float((slip["slippage"]).mean()) if not slip.empty else 0.0
med_slip   = float((slip["slippage"]).median()) if not slip.empty else 0.0

# -------------------------------
# 7) 布局与可视化
# -------------------------------
col1, col2 = st.columns([2,1])

with col1:
    st.subheader("累计 PnL（聚合后）")
    if not timeline.empty:
        chart_pnl = alt.Chart(timeline).mark_line().encode(
            x=alt.X("ts:T", title="Time"),
            y=alt.Y("cum_pnl:Q", title="Cumulative PnL"),
            tooltip=["ts:T","cum_pnl:Q","position:Q","mid:Q"]
        ).interactive()
        st.altair_chart(chart_pnl, use_container_width=True)
    else:
        st.info("时间线为空，无法绘制。")

with col2:
    st.subheader("关键指标")
    st.metric("Final PnL", f"{final_pnl:,.2f}")
    st.metric("Max Drawdown", f"{mdd:,.2f}")
    st.metric("Sharpe (approx.)", f"{sharpe:,.2f}")
    st.metric("Hit Rate", f"{hit_rate*100:.1f}%")
    st.metric("Turnover (rough)", f"{turnover:.2f}")
    st.metric("Avg Slippage", f"{avg_slip:.6f}")
    st.metric("Median Slippage", f"{med_slip:.6f}")

st.subheader("成交量随时间（聚合）")
if not timeline.empty:
    vol_bar = alt.Chart(timeline).mark_bar().encode(
        x=alt.X("ts:T", title="Time"),
        y=alt.Y("vol:Q", title="Volume"),
        tooltip=["ts:T","vol:Q","avg_price:Q"]
    )
    st.altair_chart(vol_bar, use_container_width=True)
else:
    st.info("无数据绘制成交量。")

st.subheader("净敞口 / 持仓（聚合）")
if not timeline.empty:
    pos_chart = alt.Chart(timeline).mark_line(color="orange").encode(
        x="ts:T", y=alt.Y("position:Q", title="Position"),
        tooltip=["ts:T","position:Q"]
    ).interactive()
    st.altair_chart(pos_chart, use_container_width=True)

st.subheader("滑点分布（方向调整后）")
if not slip.empty:
    slip_hist = alt.Chart(slip.dropna(subset=["slippage"])).mark_bar().encode(
        x=alt.X("slippage:Q", bin=alt.Bin(maxbins=50), title="Slippage per trade (signed)"),
        y="count()"
    )
    st.altair_chart(slip_hist, use_container_width=True)
else:
    st.info("未能计算滑点分布。")

if show_tables:
    st.divider()
    st.subheader("明细（可能较慢）")
    st.write("Timeline（聚合后）")
    st.dataframe(timeline.tail(200))
    st.write("Trades（原始）")
    st.dataframe(df_trd.tail(200))
    if not df_sig.empty:
        st.write("Signals（原始）")
        st.dataframe(df_sig.tail(200))
