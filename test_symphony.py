"""
Multi-Crop Symphony Engine:
- 100-tile expansion (NW -> NE -> SW -> SE)
- Multi-worker snake partitioning (1 worker per 6 tiles)
- Balanced Town-Demanded Portfolio:
  - 20 Melons (High-value capital accelerator)
  - 25 Strawberries (Demanded by 4 town shops: Ice Cream, Smoothie, Brunch, Farmers Market)
  - 25 Tomatoes (Demanded by Pizza Shop, Farmers Market, Town Center)
  - 30 Carrots (Rapid 3-day turnaround, highly glut-resistant)
- Immediate digging and replanting of exhausted ongoing plants
- Controlled sales pacing when market price is high
"""
import math
from kaggle_environments import make

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "bonus_start": 2, "max_yield": 6},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "ongoing": False, "bonus_start": 2, "max_yield": 4},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "ongoing": True, "bonus_start": 0, "max_yield": 4, "interval": 1},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "bonus_start": 0, "max_yield": 4, "interval": 2},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "ongoing": False, "bonus_start": 6, "max_yield": 6},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def get_step_towards(curr_pos, target_pos):
    cx, cy = curr_pos
    tx, ty = target_pos
    if cx < tx:
        return "EAST"
    if cx > tx:
        return "WEST"
    if cy < ty:
        return "SOUTH"
    if cy > ty:
        return "NORTH"
    return None


class SymphonyAgent:
    def __init__(self):
        pass

    def get_unlocked_tiles(self, farm):
        tiles = []
        board_size = len(farm["tiles"])
        for y in range(board_size):
            for x in range(board_size):
                if farm["tiles"][y][x] != "LOCKED":
                    tiles.append((x, y))
        return tiles

    def act(self, obs):
        player_id = obs["player"]
        farm = obs["farms"][player_id]
        private = obs["private"]
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        money = farm["money"]
        shed = private.get("shed", {})
        seeds = private.get("seeds", {})
        market_info = obs.get("market", {})
        prices = market_info.get("prices", {})
        
        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        unlocked_quads = len(farm["unlocked_quadrants"])

        # Workers: 1 worker per 6.2 tiles
        needed_workers = max(1, math.ceil(num_tiles / 6.2))
        target_hires = needed_workers - 1

        # --- Hour 0: Macro Strategic Planning ---
        if hour == 0:
            # 1. Land Expansion: NW -> NE ($1k) Day 0, SW ($2k) Day 6-8, SE ($4k) Day 10-14
            if unlocked_quads == 1 and money >= 1200 and day <= 20:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 2500 and day <= 16:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 3 and money >= 5000 and day <= 14:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hires
            for _ in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 3. Capital & Crop Allocation
            land_reserved = 1000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 1) else (
                2000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 2) else (
                    4000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 3) else 0
                )
            )
            avail_money = money - land_reserved - 60

            empty_count = sum(1 for (x, y) in unlocked_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(seeds.values())
            seeds_needed = max(0, empty_count - current_seeds)

            # Count active crops
            active_melons = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
            active_strawberries = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
            active_tomatoes = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "TOMATO")

            # Strawberry Engine (Demanded by 4 shops)
            if day <= 14 and avail_money >= 200:
                straw_target = 25 if num_tiles >= 75 else (15 if num_tiles >= 50 else 8)
                if active_strawberries < straw_target:
                    straw_buy = min(seeds_needed, straw_target - active_strawberries, int((avail_money * 0.4) // 100))
                    if straw_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", straw_buy])
                        seeds_needed -= straw_buy
                        avail_money -= straw_buy * 100

            # Tomato Engine (Daily ongoing harvests)
            if day <= 16 and avail_money >= 150:
                tomato_target = 25 if num_tiles >= 75 else (15 if num_tiles >= 50 else 8)
                if active_tomatoes < tomato_target:
                    tomato_buy = min(seeds_needed, tomato_target - active_tomatoes, int((avail_money * 0.35) // 50))
                    if tomato_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "TOMATO", tomato_buy])
                        seeds_needed -= tomato_buy
                        avail_money -= tomato_buy * 50

            # Melon Engine (High value burst)
            if day <= 15 and avail_money >= 160:
                melon_target = 20 if num_tiles >= 75 else 10
                if active_melons < melon_target:
                    melon_buy = min(seeds_needed, melon_target - active_melons, int((avail_money * 0.3) // 80))
                    if melon_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", melon_buy])
                        seeds_needed -= melon_buy
                        avail_money -= melon_buy * 80

            # Rapid Carrots
            if day < 27 and seeds_needed > 0 and avail_money >= 20:
                carrot_buy = min(seeds_needed, int(avail_money // 20))
                if carrot_buy > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                    seeds_needed -= carrot_buy
                    avail_money -= carrot_buy * 20
                if seeds_needed > 0 and avail_money >= 10 and len(market_orders) < 10:
                    wheat_buy = min(seeds_needed, int(avail_money // 10))
                    if wheat_buy > 0:
                        market_orders.append(["BUY_SEED", "WHEAT", wheat_buy])

        # --- Continuous Market: Sell Produce ---
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS:
                if len(market_orders) < 10:
                    market_orders.append(["SELL", item, count])

        # --- Spatial Worker Dispatcher ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        sorted_tiles = sorted(unlocked_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        chunk_size = max(1, math.ceil(len(sorted_tiles) / max(1, num_active)))
        worker_actions = []

        for w_idx, w_pos in enumerate(all_workers):
            my_tiles = sorted_tiles[w_idx * chunk_size : (w_idx + 1) * chunk_size]
            act = self._get_worker_action(w_pos, my_tiles, farm, private, day, hour)
            worker_actions.append(act)

        farmer_act = worker_actions[0] if worker_actions else ["PASS"]
        hands_acts = worker_actions[1:] if len(worker_actions) > 1 else []

        return {
            "farmer": farmer_act,
            "hands": hands_acts,
            "market": market_orders[:10],
        }

    def _get_worker_action(self, pos, assigned_tiles, farm, private, day, hour):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]

        # 1. Action on current tile
        if current_tile != "LOCKED":
            if isinstance(current_tile, dict):
                kind = current_tile.get("kind")
                if kind == "WEED":
                    return ["DIG"]
                elif kind == "PLANT":
                    crop = current_tile["crop"]
                    cd = CROPS[crop]
                    age = day - current_tile["planted_day"]
                    should_harvest = False
                    if cd["ongoing"]:
                        if current_tile.get("yield_units", 0) > 0:
                            should_harvest = True
                        else:
                            # Check if ongoing crop is exhausted
                            days_since_first = day - current_tile["planted_day"] - cd["first_yield_day"]
                            if days_since_first >= 0 and (days_since_first // cd["interval"] + 1) >= cd["max_yield"]:
                                # Dig up exhausted plant to free up tile for new planting
                                return ["DIG"]
                    else:
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]):
                            should_harvest = True
                    if should_harvest:
                        return ["HARVEST"]
                    elif not current_tile.get("watered_today", False):
                        return ["WATER"]
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "TOMATO", "MELON", "CARROT", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # 2. Find next urgent tile in assigned chunk
        target_tile = None
        for (tx, ty) in assigned_tiles:
            t = farm["tiles"][ty][tx]
            if t == "LOCKED":
                continue
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    target_tile = (tx, ty)
                    break
                elif kind == "PLANT":
                    crop = t["crop"]
                    cd = CROPS[crop]
                    age = day - t["planted_day"]
                    should_harvest = False
                    if cd["ongoing"]:
                        if t.get("yield_units", 0) > 0:
                            should_harvest = True
                        else:
                            days_since_first = day - t["planted_day"] - cd["first_yield_day"]
                            if days_since_first >= 0 and (days_since_first // cd["interval"] + 1) >= cd["max_yield"]:
                                target_tile = (tx, ty)
                                break
                    else:
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]):
                            should_harvest = True
                    if should_harvest or not t.get("watered_today", False):
                        target_tile = (tx, ty)
                        break
            elif t is None and day < 27:
                seeds = private.get("seeds", {})
                if any(v > 0 for v in seeds.values()):
                    target_tile = (tx, ty)
                    break

        if target_tile is not None:
            step = get_step_towards((cx, cy), target_tile)
            if step:
                return [step]

        # 3. Patrol home
        if assigned_tiles:
            home = assigned_tiles[0]
            if (cx, cy) != home:
                step = get_step_towards((cx, cy), home)
                if step:
                    return [step]

        return ["PASS"]


_agent_inst = None

def agent(obs):
    global _agent_inst
    if _agent_inst is None or obs.get("step", 0) == 0:
        _agent_inst = SymphonyAgent()
    return _agent_inst.act(obs)


if __name__ == "__main__":
    scores = []
    for g in range(6):
        env = make("kaggriculture", configuration={"episodeSteps": 720})
        env.run([agent, "starter"])
        s0 = env.steps[-1][0].reward
        s1 = env.steps[-1][1].reward
        scores.append(s0)
        print(f"Game {g+1}: Me=${s0:,.0f} vs Starter=${s1:,.0f}")
    print(f"Average Symphony Score: {sum(scores)/len(scores):,.2f}")
