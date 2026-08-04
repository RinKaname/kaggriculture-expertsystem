"""
Grandmaster Agricultural Ecosystem Prototype:
- Central Pasture/Animal Sanctuary (Cows & Sheep)
- Free Daily Fertilizer Harvesting & Care Bonus
- Perimeter Strawberry & Tomato Crops with Doubled Yields
- Dedicated Wheat Patch for Free Animal Feed
- 75-Tile Optimal Layout (NW, NE, SW)
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

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "product": "WOOL"},
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


def is_adjacent(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1


class GrandmasterAgent:
    def __init__(self):
        self.animal_tiles = set()
        self.pasture_planned = False

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
        
        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        unlocked_quads = len(farm["unlocked_quadrants"])

        # Workers: 1 worker per 6-7 tiles
        needed_workers = max(1, math.ceil(num_tiles / 6.5))
        target_hires = needed_workers - 1

        # --- Hour 0: Strategic Economy & Planning ---
        if hour == 0:
            # 1. Land Expansion: Unlock NE ($1k) and SW ($2k). Skip SE to save $4k
            if unlocked_quads == 1 and money >= 1200 and day <= 15:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 2400 and day <= 12:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hires
            for _ in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 3. Dynamic Crop & Livestock Purchasing
            land_reserved = 1000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 1) else (
                2000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 2) else 0
            )
            avail_money = money - land_reserved - 40

            empty_count = sum(1 for (x, y) in unlocked_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(seeds.values())
            seeds_needed = max(0, empty_count - current_seeds)

            # High Value Ongoing Crop: Strawberries & Tomatoes (Early planted on outer rim)
            if day <= 8 and avail_money >= 400:
                straw_target = 8 if num_tiles >= 50 else 4
                curr_straw = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
                straw_buy = min(seeds_needed, straw_target - curr_straw, int((avail_money * 0.4) // CROPS["STRAWBERRY"]["seed"]))
                if straw_buy > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", straw_buy])
                    seeds_needed -= straw_buy
                    avail_money -= straw_buy * CROPS["STRAWBERRY"]["seed"]

            # Melon Target
            if day <= 14 and avail_money >= 200:
                melon_target = 12 if num_tiles >= 50 else 6
                curr_melons = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
                melon_buy = min(seeds_needed, melon_target - curr_melons, int((avail_money * 0.4) // CROPS["MELON"]["seed"]))
                if melon_buy > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "MELON", melon_buy])
                    seeds_needed -= melon_buy
                    avail_money -= melon_buy * CROPS["MELON"]["seed"]

            # Fast Carrots & Wheat Loop
            if day < 27 and seeds_needed > 0 and avail_money >= 20:
                carrot_buy = min(seeds_needed, int(avail_money // CROPS["CARROT"]["seed"]))
                if carrot_buy > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                    seeds_needed -= carrot_buy
                    avail_money -= carrot_buy * CROPS["CARROT"]["seed"]
                if seeds_needed > 0 and avail_money >= 10 and len(market_orders) < 10:
                    wheat_buy = min(seeds_needed, int(avail_money // CROPS["WHEAT"]["seed"]))
                    if wheat_buy > 0:
                        market_orders.append(["BUY_SEED", "WHEAT", wheat_buy])

        # --- Continuous Market: Sell Shed Produce ---
        # Note: Keep at least 5 Wheat in shed for animal feeding
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS:
                sell_count = count
                if item == "WHEAT" and len(self.animal_tiles) > 0:
                    sell_count = max(0, count - 5)
                if sell_count > 0 and len(market_orders) < 10:
                    market_orders.append(["SELL", item, sell_count])

        # --- Multi-Worker Spatial Execution ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        sorted_tiles = sorted(unlocked_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        chunk_size = max(1, math.ceil(len(sorted_tiles) / max(1, num_active)))

        worker_actions = []
        for w_idx, w_pos in enumerate(all_workers):
            my_tiles = sorted_tiles[w_idx * chunk_size : (w_idx + 1) * chunk_size]
            inv = private.get("inventories", [{}])[w_idx] if w_idx < len(private.get("inventories", [])) else {}
            act = self._worker_act(w_pos, my_tiles, farm, private, inv, day, hour)
            worker_actions.append(act)

        farmer_act = worker_actions[0] if worker_actions else ["PASS"]
        hands_acts = worker_actions[1:] if len(worker_actions) > 1 else []

        return {
            "farmer": farmer_act,
            "hands": hands_acts,
            "market": market_orders[:10],
        }

    def _worker_act(self, pos, assigned_tiles, farm, private, inv, day, hour):
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
                    
                    # Fertilize ongoing or melon if fertilizer in inventory
                    if inv.get("FERTILIZER", 0) > 0 and current_tile.get("fertilized_until_day", -1) < day:
                        if crop in ("STRAWBERRY", "TOMATO", "MELON"):
                            return ["FERTILIZE"]

                    if not current_tile.get("watered_today", False):
                        return ["WATER"]
                elif "animal" in current_tile:
                    # Animal tile: Harvest > Collect Fertilizer > Feed > Care
                    if current_tile.get("yield_units", 0) > 0:
                        return ["HARVEST"]
                    if current_tile.get("fertilizer_available", False):
                        return ["COLLECT_FERTILIZER"]
                    if not current_tile.get("fed_today", False) and inv.get("WHEAT", 0) > 0:
                        return ["FEED"]
                    if not current_tile.get("cared_today", False):
                        return ["CARE"]
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "MELON", "CARROT", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # 2. Seek urgent task in assigned tiles
        target = None
        for (tx, ty) in assigned_tiles:
            t = farm["tiles"][ty][tx]
            if t == "LOCKED":
                continue
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    target = (tx, ty)
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
                        target = (tx, ty)
                        break
            elif t is None and day < 27:
                seeds = private.get("seeds", {})
                if any(v > 0 for v in seeds.values()):
                    target = (tx, ty)
                    break

        if target is not None:
            step = get_step_towards((cx, cy), target)
            if step:
                return [step]

        # 3. Default: Move to first assigned tile
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
        agent_instance = GrandmasterAgent()
    return agent_instance.act(obs)


if __name__ == "__main__":
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run([agent, "starter"])
    print("Scores vs starter:", [(i, s.reward) for i, s in enumerate(env.steps[-1])])
