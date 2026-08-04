"""
Grandmaster Livestock + Fertilizer + Strawberry Ecosystem Agent
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
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

SHED_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]

# Designated Pasture Sanctuary Tiles (adjacent to shed)
SANCTUARY_TILES = [(3, 4), (4, 3), (3, 3), (2, 4), (4, 2), (5, 3), (6, 3), (5, 2)]


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


class LivestockAgent:
    def __init__(self):
        self.pasture_built_count = 0
        self.animals_purchased = 0

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

        # Workers: 1 worker per 6 tiles for ultra-fast maintenance
        needed_workers = max(1, math.ceil(num_tiles / 6.0))
        target_hires = needed_workers - 1

        # Count active animals
        active_animals = 0
        empty_pastures = 0
        for (tx, ty) in unlocked_tiles:
            t = farm["tiles"][ty][tx]
            if isinstance(t, dict):
                if "animal" in t:
                    active_animals += 1
                elif t.get("kind") in ("PASTURE", "COOP"):
                    empty_pastures += 1

        # --- Hour 0: Market Planning ---
        if hour == 0:
            # 1. Land Expansion: NW -> NE ($1k) -> SW ($2k)
            if unlocked_quads == 1 and money >= 1200 and day <= 15:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 2500 and day <= 12:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hires
            for _ in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 3. Livestock Purchases (Target: 4-6 Cows in early/mid game)
            cows_in_shed = shed.get("COW", 0)
            target_cows = 4 if day >= 3 else 2
            if day <= 14 and (active_animals + cows_in_shed) < target_cows and money >= 800:
                buy_cows = min(target_cows - (active_animals + cows_in_shed), int((money * 0.5) // 400))
                if buy_cows > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_ANIMAL", "COW", buy_cows])

            # 4. Crop Seeds Purchasing
            land_reserved = 1000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 1) else (
                2000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 2) else 0
            )
            avail_money = money - land_reserved - 50

            empty_count = sum(1 for (x, y) in unlocked_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(seeds.values())
            seeds_needed = max(0, empty_count - current_seeds)

            # Ensure we have at least 15 Wheat seeds early to feed cows
            wheat_seeds = seeds.get("WHEAT", 0)
            wheat_in_shed = shed.get("WHEAT", 0)
            if (wheat_seeds + wheat_in_shed) < 10 and avail_money >= 100 and day <= 20:
                buy_w = min(10, int(avail_money // 10))
                if buy_w > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    avail_money -= buy_w * 10
                    seeds_needed = max(0, seeds_needed - buy_w)

            # High Value Strawberries on outer perimeter
            if day <= 8 and avail_money >= 300:
                curr_straw = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
                target_straw = 8 if num_tiles >= 50 else 4
                if curr_straw < target_straw:
                    straw_buy = min(seeds_needed, target_straw - curr_straw, int((avail_money * 0.4) // 100))
                    if straw_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", straw_buy])
                        seeds_needed -= straw_buy
                        avail_money -= straw_buy * 100

            # Melon Target
            if day <= 14 and avail_money >= 200:
                curr_melons = sum(1 for (x, y) in unlocked_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
                target_melons = 10 if num_tiles >= 50 else 6
                if curr_melons < target_melons:
                    melon_buy = min(seeds_needed, target_melons - curr_melons, int((avail_money * 0.4) // 80))
                    if melon_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", melon_buy])
                        seeds_needed -= melon_buy
                        avail_money -= melon_buy * 80

            # Fast Carrots
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
                sell_count = count
                # Keep wheat in shed for animal feed
                if item == "WHEAT":
                    sell_count = max(0, count - 15)
                if sell_count > 0 and len(market_orders) < 10:
                    market_orders.append(["SELL", item, sell_count])

        # --- Unit Actions ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        # Worker 0 is the Caretaker / Master Farmer
        worker_actions = []

        # Find sanctuary pastures
        sanctuary_assigned = [p for p in SANCTUARY_TILES if p in unlocked_tiles]
        field_tiles = [p for p in unlocked_tiles if p not in sanctuary_assigned]

        # Snake-order field tiles
        sorted_field = sorted(field_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        num_field_workers = max(1, num_active - 1) if num_active > 1 else 1
        chunk_size = max(1, math.ceil(len(sorted_field) / num_field_workers))

        for w_idx, w_pos in enumerate(all_workers):
            inv = private.get("inventories", [{}])[w_idx] if w_idx < len(private.get("inventories", [])) else {}
            if w_idx == 0 and num_active > 1:
                # Caretaker Worker
                act = self._caretaker_act(w_pos, sanctuary_assigned, farm, private, inv, day, hour)
            else:
                f_idx = w_idx if num_active == 1 else w_idx - 1
                my_tiles = sorted_field[f_idx * chunk_size : (f_idx + 1) * chunk_size]
                act = self._field_worker_act(w_pos, my_tiles, farm, private, inv, day, hour)
            worker_actions.append(act)

        farmer_act = worker_actions[0] if worker_actions else ["PASS"]
        hands_acts = worker_actions[1:] if len(worker_actions) > 1 else []

        return {
            "farmer": farmer_act,
            "hands": hands_acts,
            "market": market_orders[:10],
        }

    def _caretaker_act(self, pos, sanctuary_tiles, farm, private, inv, day, hour):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})

        # 1. Action on current tile
        if current_tile != "LOCKED":
            if isinstance(current_tile, dict):
                if "animal" in current_tile:
                    if current_tile.get("yield_units", 0) > 0:
                        return ["HARVEST"]
                    if current_tile.get("fertilizer_available", False):
                        return ["COLLECT_FERTILIZER"]
                    if not current_tile.get("fed_today", False) and inv.get("WHEAT", 0) > 0:
                        return ["FEED"]
                    if not current_tile.get("cared_today", False):
                        return ["CARE"]
                elif current_tile.get("kind") == "PASTURE":
                    # Place cow if in inventory
                    if inv.get("COW", 0) > 0:
                        return ["PLACE", "COW"]
                elif current_tile.get("kind") == "WEED":
                    return ["DIG"]
            elif current_tile is None and (cx, cy) in sanctuary_tiles and day <= 15:
                # Build Pasture
                return ["BUILD_PASTURE"]

        # 2. If at shed access, pick up Cow or Wheat if needed
        is_shed_adj = (cx, cy) in SHED_ACCESS
        if is_shed_adj:
            if shed.get("COW", 0) > 0 and inv.get("COW", 0) == 0:
                return ["PICKUP", "COW", 1]
            if shed.get("WHEAT", 0) > 0 and inv.get("WHEAT", 0) < 5:
                return ["PICKUP", "WHEAT", min(5, shed.get("WHEAT", 0))]

        # 3. Seek next animal or empty sanctuary task
        # First priority: Pickup cow from shed if shed has cow and we don't have one
        if shed.get("COW", 0) > 0 and inv.get("COW", 0) == 0:
            target_shed = SHED_ACCESS[0]
            step = get_step_towards((cx, cy), target_shed)
            if step:
                return [step]

        # Second priority: Pickup wheat from shed if low on feed
        if shed.get("WHEAT", 0) > 0 and inv.get("WHEAT", 0) == 0:
            target_shed = SHED_ACCESS[0]
            step = get_step_towards((cx, cy), target_shed)
            if step:
                return [step]

        # Third priority: Visit animals in sanctuary
        for (tx, ty) in sanctuary_tiles:
            t = farm["tiles"][ty][tx]
            if t == "LOCKED":
                continue
            if isinstance(t, dict) and "animal" in t:
                if t.get("yield_units", 0) > 0 or t.get("fertilizer_available", False) or (not t.get("fed_today", False) and inv.get("WHEAT", 0) > 0) or not t.get("cared_today", False):
                    step = get_step_towards((cx, cy), (tx, ty))
                    if step:
                        return [step]
            elif isinstance(t, dict) and t.get("kind") == "PASTURE" and inv.get("COW", 0) > 0:
                step = get_step_towards((cx, cy), (tx, ty))
                if step:
                    return [step]
            elif t is None and day <= 15:
                step = get_step_towards((cx, cy), (tx, ty))
                if step:
                    return [step]

        # Default: rest at shed access (4, 4)
        if (cx, cy) != (4, 4):
            step = get_step_towards((cx, cy), (4, 4))
            if step:
                return [step]

        return ["PASS"]

    def _field_worker_act(self, pos, assigned_tiles, farm, private, inv, day, hour):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]

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
                    
                    if not current_tile.get("watered_today", False):
                        return ["WATER"]
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "MELON", "CARROT", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # Target urgent tile
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
        agent_instance = LivestockAgent()
    return agent_instance.act(obs)


if __name__ == "__main__":
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run([agent, "starter"])
    print("Scores vs starter:", [(i, s.reward) for i, s in enumerate(env.steps[-1])])
