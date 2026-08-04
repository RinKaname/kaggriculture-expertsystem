from src.constants import CROPS, PRODUCTS, TOTAL_DAYS, LAND_PRICES, LAND_ORDER
from src.market import compute_market_price, compute_bulk_sell_revenue


def evaluate_crop_daily_roi(crop_name, current_day, market_prices, market_inventory=None):
    """Calculate the expected profit per tile-day for planting `crop_name` on `current_day`."""
    cd = CROPS[crop_name]
    seed_cost = cd["seed"]
    
    if not cd["ongoing"]:
        growth_days = cd["max_yield_day"]
        harvest_day = current_day + growth_days
        if harvest_day >= TOTAL_DAYS:
            # Check if first yield day fits before season end
            if current_day + cd["first_yield_day"] < TOTAL_DAYS:
                growth_days = TOTAL_DAYS - 1 - current_day
                # Estimate yield at early harvest
                bonus_days = max(0, growth_days - cd["bonus_window_start"] + 1)
                yield_units = min(cd["max_yield"], 1 + bonus_days)
            else:
                return -999.0  # Cannot mature before season ends
        else:
            # Yield at max_yield_day
            bonus_days = cd["max_yield_day"] - cd["bonus_window_start"] + 1
            yield_units = min(cd["max_yield"], 1 + bonus_days)
            
        unit_price = market_prices.get(crop_name, 25)
        revenue = yield_units * unit_price
        profit = revenue - seed_cost
        return profit / max(1, growth_days)
    else:
        # Ongoing crop
        first_day = current_day + cd["first_yield_day"]
        if first_day >= TOTAL_DAYS:
            return -999.0  # Will never yield
        
        interval = cd["interval"]
        max_productions = cd["max_yield"]
        available_days = TOTAL_DAYS - 1 - first_day
        possible_productions = min(max_productions, 1 + available_days // interval)
        if possible_productions <= 0:
            return -999.0
            
        total_growth_days = first_day - current_day + (possible_productions - 1) * interval
        unit_price = market_prices.get(crop_name, 50)
        revenue = possible_productions * unit_price
        profit = revenue - seed_cost
        return profit / max(1, total_growth_days)


def select_best_crop_portfolio(current_day, empty_tile_count, money, market_prices, market_inventory=None, active_crops=None):
    """
    Select how many seeds of each crop to buy and plant today.
    Returns: dict {crop: count}
    """
    if empty_tile_count <= 0 or money < 10:
        return {}
    
    active_crops = active_crops or {}
    active_melons = active_crops.get("MELON", 0)
    
    # Calculate ROIs
    rois = {}
    for c in CROPS:
        rois[c] = evaluate_crop_daily_roi(c, current_day, market_prices, market_inventory)
    
    portfolio = {}
    remaining_tiles = empty_tile_count
    remaining_money = money
    
    # Strategy:
    # 1. Early-to-Mid Game (Days 0-16): Plant a controlled quota of Melons (up to 12 total active) for massive profit
    if current_day <= 16 and rois.get("MELON", -1) > 0 and active_melons < 12 and remaining_money >= CROPS["MELON"]["seed"]:
        melon_quota = min(remaining_tiles, 12 - active_melons, int(remaining_money // CROPS["MELON"]["seed"]))
        # Don't spend more than 40% of cash on melons early on to preserve liquid cash
        if current_day < 5:
            melon_quota = min(melon_quota, 4)
        if melon_quota > 0:
            portfolio["MELON"] = melon_quota
            remaining_tiles -= melon_quota
            remaining_money -= melon_quota * CROPS["MELON"]["seed"]
            
    # 2. For remaining tiles, choose the highest ROI crop (typically CARROT or WHEAT)
    best_fast_crop = None
    best_fast_roi = -999.0
    for c in ["CARROT", "WHEAT"]:
        if rois.get(c, -999) > best_fast_roi:
            best_fast_roi = rois[c]
            best_fast_crop = c
            
    if best_fast_crop is None or best_fast_roi <= 0:
        # Fallback to whatever has positive ROI
        for c, r in sorted(rois.items(), key=lambda kv: -kv[1]):
            if r > 0 and remaining_money >= CROPS[c]["seed"]:
                best_fast_crop = c
                break
                
    if best_fast_crop and remaining_tiles > 0:
        seed_cost = CROPS[best_fast_crop]["seed"]
        count = min(remaining_tiles, int(remaining_money // seed_cost))
        if count > 0:
            portfolio[best_fast_crop] = portfolio.get(best_fast_crop, 0) + count
            remaining_tiles -= count
            remaining_money -= count * seed_cost

    # If still have tiles and cash, fallback to Wheat ($10)
    if remaining_tiles > 0 and remaining_money >= CROPS["WHEAT"]["seed"] and rois.get("WHEAT", -1) > 0:
        count = min(remaining_tiles, int(remaining_money // CROPS["WHEAT"]["seed"]))
        if count > 0:
            portfolio["WHEAT"] = portfolio.get("WHEAT", 0) + count
            
    return portfolio


def should_buy_land(money, unlocked_count, current_day, active_tile_count):
    """Determine whether to purchase the next quadrant."""
    if unlocked_count >= 4:
        return False
    
    n_extra = unlocked_count - 1
    if n_extra >= len(LAND_PRICES):
        return False
    cost = LAND_PRICES[n_extra]
    
    # NE quadrant ($1000): buy once we have ~$1500+ and day <= 22
    if n_extra == 0:
        return money >= 1500 and current_day <= 22
    # SW quadrant ($2000): buy once we have ~$3500+ and day <= 18
    elif n_extra == 1:
        return money >= 3500 and current_day <= 18
    # SE quadrant ($4000): buy once we have ~$7000+ and day <= 14
    elif n_extra == 2:
        return money >= 7000 and current_day <= 14
        
    return False
