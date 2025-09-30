# experiments/train.py
import argparse, os, json
import pandas as pd
import yaml
from experiments.pipeline import train_once, save_artifacts  # 仅在 experiments 内部复用

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/orderbook_top_ticks.csv")
    ap.add_argument("--model", default="logit")
    ap.add_argument("--factors", default="", help="逗号分隔因子名；留空则读 YAML")
    ap.add_argument("--factors_cfg", default="configs/factors.yaml")
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--eps", type=float, default=0.0)
    ap.add_argument("--drop_equal", action="store_true")
    ap.add_argument("--scale", action="store_true")
    ap.add_argument("--test_size", type=float, default=1.0/6.0, help="默认 5:1 切分 → 1/6")
    ap.add_argument("--outdir", default="artifacts/latest")
    args = ap.parse_args()

    df = pd.read_csv(args.data)

    if args.factors.strip():
        factor_names = [s.strip() for s in args.factors.split(",") if s.strip()]
    else:
        try:
            cfg = yaml.safe_load(open(args.factors_cfg))
            factor_names = [f["name"] for f in cfg["factors"]]
        except Exception:
            factor_names = ["momentum_5"]

    res = train_once(
        df_ticks=df,
        factor_names=factor_names,
        model_name=args.model,
        horizon=args.horizon,
        eps=args.eps,
        drop_equal=args.drop_equal,
        test_size=args.test_size,
        scale=args.scale,
    )

    os.makedirs(args.outdir, exist_ok=True)
    save_artifacts(args.outdir, res, extra_meta={
        "factors": factor_names,
        "horizon": args.horizon,
        "eps": args.eps,
        "test_size": args.test_size
    })

    # 训练结果简报（给 API 读取）
    with open(os.path.join(args.outdir, "meta.json"), "r") as f:
        meta = json.load(f)
    print(json.dumps(meta))  # stdout 打印 JSON，API 可忽略也可解析

if __name__ == "__main__":
    main()
