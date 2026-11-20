"""
Chakula-Smart: Sensitivity analysis
Je, ni saa gani ya kuanza punguzo, na punguzo la juu kiasi gani, vinatoa matokeo bora?
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import run, summarize, DATA_DIR
from pricing_engine import PricingConfig

START_HOURS = [15, 17, 19, 21, 22]
MAX_DISCOUNTS = [0.30, 0.40, 0.50, 0.60]


def label(h: float) -> str:
    h = int(h)
    n = ((h - 6) % 12) or 12
    return f"saa {n} " + ("mchana" if h < 16 else "jioni" if h < 19 else "usiku")


def experiment(df, configs):
    rows = []
    for name, cfg in configs:
        s = summarize(run(cfg, df))
        rows.append({
            "Mpangilio": name,
            "Upotevu (%)": round(s["waste_after"], 1),
            "Faida (TSh M)": round(s["profit_after"] / 1e6, 2),
            "Faida iliyoongezeka (TSh M)": round((s["profit_after"] - s["profit_before"]) / 1e6, 2),
            "Sahani zilizookolewa": s["rescued"],
            "Sahani za punguzo": s["discounted"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "sales_hourly.csv")

    print("\n1) Punguzo linaanza saa ngapi? (punguzo la juu = 50%)")
    t1 = experiment(df, [(f"Linaanza {label(h)}", PricingConfig(start_hour=h)) for h in START_HOURS])
    print(t1.to_string(index=False))
    t1.to_csv(DATA_DIR / "sensitivity_start_hour.csv", index=False)

    print("\n2) Punguzo la juu kabisa liwe kiasi gani? (linaanza saa 4 usiku)")
    t2 = experiment(df, [(f"Juu {int(m * 100)}%", PricingConfig(max_discount=m)) for m in MAX_DISCOUNTS])
    print(t2.to_string(index=False))
    t2.to_csv(DATA_DIR / "sensitivity_max_discount.csv", index=False)

    best = t1.loc[t1["Faida (TSh M)"].idxmax()]
    print(f"\nFaida kubwa zaidi: {best['Mpangilio']} (TSh {best['Faida (TSh M)']}M)")