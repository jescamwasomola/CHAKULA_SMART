"""
Chakula-Smart: Elasticity sensitivity
Je, matokeo yanabadilikaje kama dhana ya ELASTICITY si sahihi?
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest
from backtest import run, summarize, DATA_DIR
from pricing_engine import PricingConfig

ELASTICITIES = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]

if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "sales_hourly.csv")
    cfg = PricingConfig()
    rows = []

    for e in ELASTICITIES:
        backtest.ELASTICITY = e          # badilisha dhana kisha endesha tena
        s = summarize(run(cfg, df))
        rows.append({
            "Elasticity": e,
            "Upotevu (%)": round(s["waste_after"], 1),
            "Faida (TSh M)": round(s["profit_after"] / 1e6, 2),
            "Faida iliyoongezeka (TSh M)": round((s["profit_after"] - s["profit_before"]) / 1e6, 2),
            "Sahani zilizookolewa": s["rescued"],
        })

    out = pd.DataFrame(rows)
    print("\nPunguzo linaanza saa 11 jioni, punguzo la juu 50%")
    print("(Elasticity 2.0 = dhana ya sasa: 1% punguzo -> 2% mahitaji)\n")
    print(out.to_string(index=False))
    out.to_csv(DATA_DIR / "sensitivity_elasticity.csv", index=False)

    import numpy as np
    gain = out["Faida iliyoongezeka (TSh M)"].to_numpy()
    e_break = float(np.interp(0, gain, out["Elasticity"].to_numpy()))
    print(f"\nMfumo unavunja sawa kwa elasticity ~{e_break:.2f}. "
          f"Chini ya hapo, punguzo linakula mapato kuliko linavyoleta wateja wapya.")