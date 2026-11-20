"""
Chakula-Smart: Je, kizingiti cha salio au punguzo dogo la juu vinafanya mfumo uwe imara?
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest
from backtest import run, summarize, DATA_DIR
from pricing_engine import PricingConfig

ELASTICITIES = [1.0, 1.5, 2.0]


def grid(df, configs):
    gain, waste = {}, {}
    for name, cfg in configs:
        gain[name], waste[name] = {}, {}
        for e in ELASTICITIES:
            backtest.ELASTICITY = e
            s = summarize(run(cfg, df))
            gain[name][e] = round((s["profit_after"] - s["profit_before"]) / 1e6, 2)
            waste[name][e] = round(s["waste_after"], 1)
    g = pd.DataFrame(gain).T
    w = pd.DataFrame(waste).T
    g.columns = w.columns = [f"e={e}" for e in ELASTICITIES]
    return g, w


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "sales_hourly.csv")

    print("\nA) Kizingiti cha salio (hakuna punguzo kama salio linalotarajiwa ni chini ya kizingiti)")
    cfgs = [(f"Kizingiti {int(t * 100)}%", PricingConfig(min_surplus=t)) for t in [0.0, 0.2, 0.4, 0.6]]
    g, w = grid(df, cfgs)
    print("\nFaida iliyoongezeka (TSh M)\n", g.to_string())
    print("\nUpotevu (%)\n", w.to_string())
    g.to_csv(DATA_DIR / "robustness2_threshold.csv")

    print("\n\nB) Punguzo la juu kabisa (linaanza saa 11 jioni)")
    cfgs = [(f"Juu {int(m * 100)}%", PricingConfig(max_discount=m)) for m in [0.2, 0.3, 0.4, 0.5]]
    g, w = grid(df, cfgs)
    print("\nFaida iliyoongezeka (TSh M)\n", g.to_string())
    print("\nUpotevu (%)\n", w.to_string())
    g.to_csv(DATA_DIR / "robustness2_maxdisc.csv")