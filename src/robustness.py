"""
Chakula-Smart: Robustness test
Je, kutegemea zaidi salio (si saa) kunafanya mfumo uwe imara hata elasticity ikiwa ndogo?
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest
from backtest import run, summarize, DATA_DIR
from pricing_engine import PricingConfig

WEIGHTS = [
    (0.4, 0.6, "Sasa: 40% muda / 60% salio"),
    (0.2, 0.8, "20% muda / 80% salio"),
    (0.0, 1.0, "Salio pekee"),
]
ELASTICITIES = [0.5, 1.0, 1.5, 2.0]

if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "sales_hourly.csv")
    gain, waste = {}, {}

    for tw, sw, name in WEIGHTS:
        cfg = PricingConfig(time_weight=tw, surplus_weight=sw)
        gain[name], waste[name] = {}, {}
        for e in ELASTICITIES:
            backtest.ELASTICITY = e
            s = summarize(run(cfg, df))
            gain[name][e] = round((s["profit_after"] - s["profit_before"]) / 1e6, 2)
            waste[name][e] = round(s["waste_after"], 1)

    g = pd.DataFrame(gain).T
    g.columns = [f"e={e}" for e in ELASTICITIES]
    w = pd.DataFrame(waste).T
    w.columns = [f"e={e}" for e in ELASTICITIES]

    print("\nFaida iliyoongezeka (TSh M), kwa elasticity tofauti\n")
    print(g.to_string())
    print("\nUpotevu wa chakula (%), kwa elasticity tofauti\n")
    print(w.to_string())
    g.to_csv(DATA_DIR / "robustness_profit.csv")