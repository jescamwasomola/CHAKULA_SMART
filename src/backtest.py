"""
Chakula-Smart: Backtest
Inaendesha injini ya bei juu ya data ya siku 30 na kulinganisha na hali ya kawaida.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pricing_engine import calculate_price, PricingConfig

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Dhana: kila 1% ya punguzo huongeza mahitaji kwa 2% (wateja wapya wa kipato cha chini).
# Hii ni makadirio; kwenye data halisi tungeipima kutokana na mauzo.
ELASTICITY = 2.0


def run(cfg: PricingConfig = None, df: pd.DataFrame = None) -> pd.DataFrame:
    cfg = cfg or PricingConfig()
    if df is None:
        df = pd.read_csv(DATA_DIR / "sales_hourly.csv")
    rows = []

    for (date, vid, dish), g in df.groupby(["date", "vendor_id", "dish"]):
        g = g.sort_values("hour")
        prepared = int(g.prepared.iloc[0])
        base = int(g.price_tsh.iloc[0])
        cost = int(g.cost_tsh.iloc[0])
        area = g.area.iloc[0]

        base_sold = int(g.sold_in_hour.sum())
        base_profit = base_sold * base - prepared * cost

        remaining = prepared
        sold_hist, revenue, discounted_meals = [], 0.0, 0
        for hour, demand in zip(g.hour, g.demand_in_hour):
            rate = float(np.mean(sold_hist[-3:])) if sold_hist else 0.0
            d = calculate_price(base, cost, remaining, float(hour), rate, cfg)
            adj_demand = int(round(demand * (1 + ELASTICITY * d.discount_pct / 100)))
            sold = min(adj_demand, remaining)
            remaining -= sold
            sold_hist.append(sold)
            revenue += sold * d.price
            if d.price < base:
                discounted_meals += sold

        rows.append({
            "date": date, "vendor_id": vid, "area": area, "dish": dish,
            "prepared": prepared, "cost": cost,
            "base_sold": base_sold, "base_profit": base_profit,
            "new_sold": prepared - remaining, "new_profit": revenue - prepared * cost,
            "discounted_meals": discounted_meals,
        })

    return pd.DataFrame(rows)


def summarize(res: pd.DataFrame) -> dict:
    prepared = res.prepared.sum()
    return {
        "waste_before": (prepared - res.base_sold.sum()) / prepared * 100,
        "waste_after": (prepared - res.new_sold.sum()) / prepared * 100,
        "loss_before": ((res.prepared - res.base_sold) * res.cost).sum(),
        "loss_after": ((res.prepared - res.new_sold) * res.cost).sum(),
        "profit_before": res.base_profit.sum(),
        "profit_after": res.new_profit.sum(),
        "rescued": int(res.new_sold.sum() - res.base_sold.sum()),
        "discounted": int(res.discounted_meals.sum()),
    }


if __name__ == "__main__":
    res = run()
    res.to_csv(DATA_DIR / "backtest_results.csv", index=False)
    s = summarize(res)

    print("=" * 58)
    print("  MATOKEO YA BACKTEST: Chakula-Smart (siku 30, wauzaji 15)")
    print("=" * 58)
    print(f"Upotevu wa chakula   : {s['waste_before']:5.1f}%  ->  {s['waste_after']:5.1f}%")
    print(f"Hasara ya chakula    : TSh {s['loss_before']:>12,.0f}  ->  TSh {s['loss_after']:>12,.0f}")
    print(f"Faida ya jumla       : TSh {s['profit_before']:>12,.0f}  ->  TSh {s['profit_after']:>12,.0f}")
    print(f"Faida iliyoongezeka  : TSh {s['profit_after'] - s['profit_before']:>12,.0f}")
    print(f"Sahani zilizookolewa : {s['rescued']:,}")
    print(f"Sahani za punguzo    : {s['discounted']:,} (kwa wateja wa kipato cha chini)")
    print(f"\nMatokeo kamili: {DATA_DIR / 'backtest_results.csv'}")