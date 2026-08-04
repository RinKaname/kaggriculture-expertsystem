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

MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}


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


class AdvancedFarmAgent:
    def __init__(self):
        self.last_day = -1

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
        market_info = obs.get("market", {})
        prices = market_info.get("prices", {})
        
        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        unlocked_quads = len(farm["unlocked_quadrants"])

        # Workers: 1 worker per 7-8 tiles to ensure 100% daily watering & harvesting
        needed_workers = max(1, math.ceil(num_tiles / 7.5))
        target_hires = needed_workers - 1

        # --- Hour 0: Daily Strategic Planning & Purchasing ---
        if hour == 0:
            # 1. Land Expansion Logic
            if unlocked_quads == 1 and money >= 1500 and day <= 22:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 3000 and day <= 18:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 3 and money >= 6000 and day <= 14:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hires
            for h in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 3. Dynamic Crop Portfolio Selection
            # Count empty tiles and active seeds
            empty_count = sum(1 for (x, y) in unlocked_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(private.get("seeds", {}).values())
            seeds_needed = max(0, empty_count - current_seeds)

            avail_money = money - (1000 if "BUY_LAND" in [o[0] for o in market_orders] else 0) - 50

            if seeds_needed > 0 and avail_money > 20:
                if day >= 27:
                    # Season almost over: don't plant new seeds
                    pass
                elif day >= 26:
                    # 4 days remaining: plant CARROT (2-3 days)
                    c_buy = min(seeds_needed, int(avail_money // CROPS["CARROT"]["seed"]))
                    if c_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", c_buy])
                elif day >= 24:
                    # 6 days remaining: CARROT / WHEAT
                    c_buy = min(seeds_needed, int(avail_money // CROPS["CARROT"]["seed"]))
                    if c_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", c_buy])
                elif day <= 16:
                    # Early-Mid game: Controlled Melons + high-density Carrots
                    active_melons = 0
                    for (tx, ty) in unlocked_tiles:
                        t = farm["tiles"][ty][tx]
                        if isinstance(t, dict) and t.get("crop") == "MELON":
                            active_melons += 1
                    
                    # Target up to 10 active melons to maximize high-value yield without crashing price
                    melon_target = 10
                    melon_buy = 0
                    if active_melons < melon_target and avail_money >= 160:
                        melon_buy = min(seeds_needed, melon_target - active_melons, int((avail_money * 0.4) // CROPS["MELON"]["seed"]))
                        if melon_buy > 0:
                            market_orders.append(["BUY_SEED", "MELON", melon_buy])
                            seeds_needed -= melon_buy
                            avail_money -= melon_buy * CROPS["MELON"]["seed"]
                    
                    # Remaining tiles: Carrot
                    carrot_buy = min(seeds_needed, int(avail_money // CROPS["CARROT"]["seed"]))
                    if carrot_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                        seeds_needed -= carrot_buy
                        avail_money -= carrot_buy * CROPS["CARROT"]["seed"]
                        
                    if seeds_needed > 0 and avail_money >= CROPS["WHEAT"]["seed"]:
                        wheat_buy = min(seeds_needed, int(avail_money // CROPS["WHEAT"]["seed"]))
                        if wheat_buy > 0:
                            market_orders.append(["BUY_SEED", "WHEAT", wheat_buy])
                else:
                    # Mid-Late game (Days 17-23): Fast turnaround Carrots
                    carrot_buy = min(seeds_needed, int(avail_money // CROPS["CARROT"]["seed"]))
                    if carrot_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                    elif avail_money >= CROPS["WHEAT"]["seed"]:
                        wheat_buy = min(seeds_needed, int(avail_money // CROPS["WHEAT"]["seed"]))
                        if wheat_buy > 0:
                            market_orders.append(["BUY_SEED", "WHEAT", wheat_buy])

        # --- Continuous Market: Sell Produce ---
        shed = private.get("shed", {})
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS:
                if len(market_orders) < 10:
                    market_orders.append(["SELL", item, count])

        # --- Reactive Spatial Worker Dispatcher ---
        all_workers_pos = [farm["farmer"]] + farm.get("hands", [])
        num_active_workers = len(all_workers_pos)

        # Snake-order sorting of unlocked tiles
        sorted_tiles = sorted(unlocked_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))

        chunk_size = max(1, math.ceil(len(sorted_tiles) / max(1, num_active_workers)))
        worker_actions = []

        for w_idx, w_pos in enumerate(all_workers_pos):
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
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]):
                            should_harvest = True
                    if should_harvest:
                        return ["HARVEST"]
                    elif not current_tile.get("watered_today", False):
                        return ["WATER"]
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["MELON", "CARROT", "WHEAT"]:
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


agent_instance = None

def agent(obs):
    global agent_instance
    if agent_instance is None or obs.get("step", 0) == 0:
        agent_instance = AdvancedFarmAgent()
    return agent_instance.act(obs)


if __name__ == "__main__":
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run([agent, "starter"])
    print("Scores vs starter:", [(i, s.reward) for i, s in enumerate(env.steps[-1])])
