"""
Chakula-Smart: Rule-Based Dynamic Pricing Engine
Inapiga hesabu ya punguzo kulingana na muda uliobaki na kasi ya mauzo.
"""
import math
from dataclasses import dataclass


@dataclass
class PricingConfig:
    start_hour: float = 17.0        # saa 11 jioni: punguzo linaanza
    close_hour: float = 24.0        # saa 6 usiku: soko linafungwa
    max_discount: float = 0.30      # punguzo kubwa kabisa (30%): 2,000 -> 1,400
    floor_cost_ratio: float = 0.70  # bei haishuki chini ya 70% ya gharama
    time_weight: float = 0.4        # uzito wa muda
    surplus_weight: float = 0.6     # uzito wa salio linalotarajiwa kubaki
    round_to: int = 100             # bei inakadiriwa hadi TSh 100
    notify_min_discount: float = 0.15  # SMS inatumwa kama punguzo >= 15%
    min_surplus: float = 0.0        # hakuna punguzo kama salio linalotarajiwa ni chini ya hiki

@dataclass
class PriceDecision:
    price: int
    base_price: int
    discount_pct: float
    projected_unsold: float
    reason: str
    notify: bool


def _round_up(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def _round_nearest(value: float, step: int) -> int:
    return int(math.floor(value / step + 0.5) * step)


def calculate_price(
    base_price: int,
    cost: int,
    remaining: int,
    hour: float,
    recent_rate: float,
    cfg: PricingConfig = PricingConfig(),
) -> PriceDecision:
    """
    base_price  : bei ya kawaida (TSh)
    cost        : gharama ya kupika sahani moja (TSh)
    remaining   : sahani zilizobaki sasa hivi
    hour        : saa ya sasa kwa desimali, mfumo wa 24h (22.5 = saa 4:30 usiku)
    recent_rate : kasi ya mauzo, sahani kwa saa (wastani wa saa 3 zilizopita)
    """
    if remaining <= 0:
        return PriceDecision(base_price, base_price, 0.0, 0.0, "Chakula kimeisha", False)

    if hour < cfg.start_hour:
        return PriceDecision(base_price, base_price, 0.0, 0.0, "Bado muda wa bei ya kawaida", False)

    window = cfg.close_hour - cfg.start_hour
    time_pressure = min(max((hour - cfg.start_hour) / window, 0.0), 1.0)

    hours_left = max(cfg.close_hour - hour, 0.0)
    projected_unsold = max(0.0, remaining - recent_rate * hours_left)
    surplus_pressure = projected_unsold / remaining
    if surplus_pressure < cfg.min_surplus:
        return PriceDecision(base_price, base_price, 0.0, round(projected_unsold, 1),
                             "Mauzo yanaenda vizuri, hakuna haja ya punguzo", False)

    raw = cfg.time_weight * time_pressure + cfg.surplus_weight * surplus_pressure
    discount = min(cfg.max_discount * raw, cfg.max_discount)

    floor_price = _round_up(cost * cfg.floor_cost_ratio, cfg.round_to)
    price = _round_nearest(base_price * (1 - discount), cfg.round_to)
    price = int(min(max(price, floor_price), base_price))

    actual_discount = 1 - price / base_price
    if actual_discount < 0.01:
        reason = "Mauzo yanaenda vizuri, hakuna haja ya punguzo"
    elif price == floor_price:
        reason = "Bei imefika sakafu ya kulinda mtaji"
    else:
        reason = "Muda unakaribia kuisha na salio bado kubwa"

    return PriceDecision(
        price=price,
        base_price=base_price,
        discount_pct=round(actual_discount * 100, 1),
        projected_unsold=round(projected_unsold, 1),
        reason=reason,
        notify=actual_discount >= cfg.notify_min_discount,
    )


def _swahili_clock(hour: float) -> str:
    h = int(hour) % 24
    n = ((h - 6) % 12) or 12
    if h < 4:
        period = "usiku"
    elif h < 6:
        period = "alfajiri"
    elif h < 12:
        period = "asubuhi"
    elif h < 16:
        period = "mchana"
    elif h < 19:
        period = "jioni"
    else:
        period = "usiku"
    return f"saa {n} {period}"


def build_sms(dish: str, vendor: str, area: str, d: PriceDecision, close_hour: float = 24.0) -> str:
    """Ujumbe mfupi kwa wateja wa kipato cha chini walio karibu."""
    return (
        f"CHAKULA SASA! {dish} TSh {d.price:,} badala ya TSh {d.base_price:,} "
        f"(punguzo {d.discount_pct:.0f}%). {vendor}, {area}. "
        f"Hadi {_swahili_clock(close_hour)}."
    )


if __name__ == "__main__":
    scenarios = [
        ("Saa 3:00 usiku, bado bei ya kawaida", 21.0, 40, 2),
        ("Saa 4:00 usiku, mauzo polepole", 22.0, 40, 2),
        ("Saa 4:30 usiku, mauzo polepole", 22.5, 35, 3),
        ("Saa 5:30 usiku, salio kubwa", 23.5, 30, 2),
        ("Saa 4:00 usiku, mauzo mazuri", 22.0, 10, 8),
        ("Saa 5:00 usiku, chakula kimeisha", 23.0, 0, 5),
    ]
    print(f"{'Hali':<38}{'Bei':>7}{'Punguzo':>10}   Sababu")
    print("-" * 97)
    for label, hr, remaining, rate in scenarios:
        d = calculate_price(2000, 1100, remaining, hr, rate)
        print(f"{label:<38}{d.price:>7,}{d.discount_pct:>9.0f}%   {d.reason}")

    print("\nMfano wa SMS:")
    d = calculate_price(2000, 1100, 30, 23.5, 2)
    print(build_sms("Wali Maharage", "Mama Ntilie #3", "Ubungo", d))