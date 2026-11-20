"""
Chakula-Smart: Synthetic data generator
Inatengeneza mauzo ya saa-kwa-saa ya Mama Ntilie wa Dar es Salaam kwa siku 30.
Soko linafunguliwa saa 12 asubuhi (06:00) hadi saa 6 usiku (24:00).
"""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Saa (24h) -> uzito wa mahitaji (jumla = 1.0)
# Kifungua kinywa, mchana (kilele), jioni, na usiku (bodaboda/vibarua)
HOUR_WEIGHTS = {
    6: .04, 7: .06, 8: .05, 9: .03, 10: .03, 11: .06, 12: .12, 13: .13,
    14: .07, 15: .03, 16: .03, 17: .04, 18: .06, 19: .07, 20: .06,
    21: .05, 22: .04, 23: .03,
}

AREAS = {
    "Kariakoo": (1.10, 1.30), "Ubungo": (1.00, 1.20), "Mwenge": (1.05, 1.10),
    "Mbagala": (0.90, 1.00), "Tegeta": (0.90, 0.90), "Sinza": (1.05, 1.00),
    "Temeke": (0.90, 1.10), "Kimara": (0.95, 1.00),
}

# Chakula: (bei ya kuuza TSh, gharama ya kupika TSh, mahitaji ya msingi kwa siku)
DISHES = {
    "Wali Maharage":    (2000, 1100, 60),
    "Wali Nyama":       (4000, 2500, 35),
    "Ugali Dagaa":      (2500, 1500, 40),
    "Pilau":            (3000, 1800, 30),
    "Chapati Maharage": (1500, 800, 45),
}

N_VENDORS = 15
N_DAYS = 30


def build_vendors() -> pd.DataFrame:
    areas = list(AREAS)
    rows = []
    for i in range(1, N_VENDORS + 1):
        area = areas[(i - 1) % len(areas)]
        price_f, pop_f = AREAS[area]
        rows.append({
            "vendor_id": f"MN{i:03d}",
            "vendor_name": f"Mama Ntilie #{i}",
            "area": area,
            "price_factor": price_f,
            "popularity": round(pop_f * rng.uniform(0.7, 1.3), 2),
            "overcook_factor": round(rng.uniform(1.15, 1.70), 2),
        })
    return pd.DataFrame(rows)


def simulate() -> pd.DataFrame:
    vendors = build_vendors()
    vendors.to_csv(DATA_DIR / "vendors.csv", index=False)

    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=N_DAYS)
    records = []

    for date in dates:
        weekend = date.weekday() >= 5
        rain = rng.random() < 0.2
        day_factor = (0.85 if weekend else 1.0) * (0.75 if rain else 1.0)

        for _, v in vendors.iterrows():
            for dish, (base_price, cost, base_demand) in DISHES.items():
                price = int(round(base_price * v.price_factor / 100) * 100)
                demand_day = base_demand * v.popularity * day_factor * rng.uniform(0.85, 1.15)
                prepared = int(base_demand * v.popularity * v.overcook_factor)
                remaining = prepared

                for hour, w in HOUR_WEIGHTS.items():
                    demand = int(rng.poisson(demand_day * w))
                    sold = int(min(demand, remaining))
                    remaining -= sold
                    records.append({
                        "date": date.date(), "vendor_id": v.vendor_id,
                        "vendor_name": v.vendor_name, "area": v.area,
                        "dish": dish, "hour": hour, "price_tsh": price,
                        "cost_tsh": cost, "prepared": prepared,
                        "demand_in_hour": demand,
                        "sold_in_hour": sold, "remaining_after_hour": remaining,
                        "is_weekend": int(weekend), "is_rainy": int(rain),
                    })

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = simulate()
    out = DATA_DIR / "sales_hourly.csv"
    df.to_csv(out, index=False)

    day = df.groupby(["date", "vendor_id", "dish"]).agg(
        prepared=("prepared", "first"),
        sold=("sold_in_hour", "sum"),
        cost=("cost_tsh", "first"),
    )
    day["wasted"] = day.prepared - day.sold
    waste_pct = day.wasted.sum() / day.prepared.sum() * 100
    loss = (day.wasted * day.cost).sum()

    print(f"Safu zilizotengenezwa : {len(df):,}")
    print(f"Faili                 : {out}")
    print(f"Chakula kinachopotea  : {waste_pct:.1f}% ya kilichopikwa")
    print(f"Hasara ya mtaji (siku 30, wauzaji {N_VENDORS}): TSh {loss:,.0f}")