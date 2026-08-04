import math
from src.constants import MARKET_PARAMS, MARKET_I0, PRICE_FLOOR, PRODUCTS, CROPS, ANIMALS, SHOPS, TOWN_CENTER_PRODUCTS, TOWN_CENTER_DEMAND_SCHEDULE


def shape_func(func_name, x):
    x = max(0.0, float(x))
    if func_name == "linear":
        return x
    if func_name == "sq":
        return x * x
    if func_name == "sqrt":
        return math.sqrt(x)
    if func_name == "log":
        return math.log(1.0 + x)
    if func_name == "log10":
        return math.log10(1.0 + x)
    return x


def compute_market_price(item, inventory, params=None):
    """Compute sale price for 1 unit given the current market inventory."""
    p = (params or MARKET_PARAMS)[item]
    base = p["base"]
    I0 = p["I0"]
    T = p["T"]
    if inventory < I0:
        f = p["below_func"]
        amp = p["below_target"] * base / shape_func(f, T)
        price = base + amp * shape_func(f, I0 - inventory)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / shape_func(f, T)
        price = base - amp * shape_func(f, inventory - I0)
    return max(PRICE_FLOOR, int(round(price)))


def compute_bulk_sell_revenue(item, current_inventory, quantity, params=None):
    """Compute total revenue if selling `quantity` units sequentially."""
    if quantity <= 0:
        return 0, current_inventory
    p = (params or MARKET_PARAMS)[item]
    total_rev = 0
    inv = current_inventory
    for _ in range(quantity):
        price = compute_market_price(item, inv, params)
        total_rev += price
        if price > PRICE_FLOOR:
            inv += 1
    return total_rev, inv


def project_town_consumption(unlocked_shops, day, days_ahead=1):
    """Estimate total town consumption per product over the next `days_ahead` days."""
    consumption = {p: 0 for p in PRODUCTS}
    
    # 24 turns per day.
    # Town shops consume every 4 turns -> 6 times per day.
    for shop in unlocked_shops:
        if shop not in SHOPS:
            continue
        prods = SHOPS[shop]
        mult = 2 if len(prods) == 1 else 1
        for p in prods:
            consumption[p] += 6 * mult * days_ahead

    # Town center consumes every 12 turns -> 2 times per day.
    center_mult = 1
    for threshold, m in TOWN_CENTER_DEMAND_SCHEDULE:
        if day >= threshold:
            center_mult = m
            break
    for p in TOWN_CENTER_PRODUCTS:
        consumption[p] += 2 * center_mult * days_ahead

    return consumption
