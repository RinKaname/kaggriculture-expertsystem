import math

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "bonus_start": 2, "max_yield": 6, "base_price": 25},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "bonus_start": 0, "max_yield": 4, "interval": 2, "base_price": 120},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "ongoing": False, "bonus_start": 6, "max_yield": 6, "base_price": 250},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

NW_PASTURES = [(4, 4), (4, 3), (4, 2), (3, 4), (3, 3)] # 5 in NW
NE_PASTURES = [(5, 4), (5, 3), (6, 3), (6, 4)] # 4 in NE
SW_PASTURES = [(4, 5), (3, 5), (4, 6), (3, 6), (2, 6)] # 5 in SW, Total 14

SHED_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]

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

class AgentJules:
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

    def get_target_pastures(self, unlocked_quads):
        p = list(NW_PASTURES)
        if "NE" in unlocked_quads:
            p += NE_PASTURES
        if "SW" in unlocked_quads:
            p += SW_PASTURES
        return p[:14]

    def act(self, obs):
        player_id = obs["player"]
        farm = obs["farms"][player_id]
        private = obs["private"]
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        step = obs.get("step", 0)
        money = farm["money"]
        shed = private.get("shed", {})
        seeds = private.get("seeds", {})
        inventories = private.get("inventories", [])
        market_info = obs.get("market", {})
        prices = market_info.get("prices", {})
        unlocked_quads = farm["unlocked_quadrants"]

        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        target_pastures = self.get_target_pastures(unlocked_quads)

        placed_animals = sum(1 for (px, py) in target_pastures if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) and isinstance(farm["tiles"][py][px], dict) and "animal" in farm["tiles"][py][px])
        shed_animals = shed.get("COW", 0) + shed.get("SHEEP", 0)
        inv_animals = sum(inv.get("COW", 0) + inv.get("SHEEP", 0) for inv in inventories)
        total_animals = placed_animals + shed_animals + inv_animals

        # 2. Market Arbitrage & Actions (Hour 0)
        # 2. Market Arbitrage
        quads = len(unlocked_quads)
        target_workers = 6 if quads == 1 else (8 if quads == 2 else 12)
        current_workers = 1 + len(farm.get("hands", []))
        hires_to_make = min(2, target_workers - current_workers)
        if hour == 0 and target_workers > current_workers and money >= 10:
            for _ in range(hires_to_make):
                market_orders.append(["HIRE"])

        if hour == 0:

            # Land Expansion
            if quads == 1 and day >= 7 and money >= 1000:
                market_orders.append(["BUY_LAND"])
            elif quads == 2 and day >= 10 and money >= 2000:
                market_orders.append(["BUY_LAND"])

            # Buy Wheat for animals
            if total_animals > 0:
                wheat_needed = (total_animals * 2) - shed.get("WHEAT", 0)
                if wheat_needed > 0 and money >= wheat_needed * prices.get("WHEAT", 25):
                    market_orders.append(["BUY_PRODUCT", "WHEAT", wheat_needed])

            # Buy Animals (up to 14)
            if total_animals < len(target_pastures):
                # Dynamically tilt towards higher value
                milk_price = prices.get("MILK", 160)
                wool_price = prices.get("WOOL", 200)
                diff = abs(milk_price - wool_price) / float(max(milk_price, wool_price))

                num_cows = sum(1 for (px, py) in target_pastures if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) and isinstance(farm["tiles"][py][px], dict) and farm["tiles"][py][px].get("animal") == "COW")
                num_cows += shed.get("COW", 0) + sum(inv.get("COW", 0) for inv in inventories)

                num_sheep = total_animals - num_cows

                if diff > 0.3:
                    best_animal = "COW" if milk_price > wool_price else "SHEEP"
                else:
                    best_animal = "COW" if num_cows <= num_sheep else "SHEEP"

                animal_cost = 400 if best_animal == "COW" else 500
                if money >= animal_cost:
                    market_orders.append(["BUY_ANIMAL", best_animal, 1])

            # Buy Crop Seeds (Strawberry & Melon focus)
            crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
            empty_crop_tiles = sum(1 for (x, y) in crop_tiles if farm["tiles"][y][x] is None)
            total_seeds_held = sum(seeds.values())

            if day < 23 and empty_crop_tiles > total_seeds_held:
                seeds_to_buy = empty_crop_tiles - total_seeds_held
                # 60% Strawberry, 40% Melon
                straw_wanted = int(seeds_to_buy * 0.6)
                melon_wanted = seeds_to_buy - straw_wanted

                if straw_wanted > 0: market_orders.append(["BUY_SEED", "STRAWBERRY", straw_wanted])
                if melon_wanted > 0: market_orders.append(["BUY_SEED", "MELON", melon_wanted])

        # Fallback Wheat Planting (if very poor or end game)
        if money < 50 or (25 <= day <= 27):
            crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
            empty_crop_tiles = sum(1 for (x, y) in crop_tiles if farm["tiles"][y][x] is None)
            if empty_crop_tiles > 0 and seeds.get("WHEAT", 0) == 0:
                market_orders.append(["BUY_SEED", "WHEAT", 1])

        # Sell all produce
        sellable = []
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS and item not in ["WHEAT", "COW", "SHEEP", "GOOSE"]:
                sellable.append((item, count, count * prices.get(item, 1)))

        sellable.sort(key=lambda x: x[2], reverse=True)
        for item, count, _ in sellable:
            market_orders.append(["SELL", item, count])

        market_orders = market_orders[:10]

        # 3. Worker Fleet Dispatch
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        sorted_crop_tiles = sorted([pos for pos in unlocked_tiles if pos not in target_pastures], key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        chunk_size = max(1, math.ceil(len(sorted_crop_tiles) / max(1, num_active)))
        worker_actions = []

        for w_idx, w_pos in enumerate(all_workers):
            inv = inventories[w_idx] if w_idx < len(inventories) else {}
            my_tiles = sorted_crop_tiles[w_idx * chunk_size : (w_idx + 1) * chunk_size]
            act = self._get_worker_action(w_pos, my_tiles, target_pastures, farm, private, day, hour, inv, w_idx, step, total_animals)
            worker_actions.append(act)

        return {
            "farmer": worker_actions[0] if worker_actions else ["PASS"],
            "hands": worker_actions[1:] if len(worker_actions) > 1 else [],
            "market": market_orders,
        }

    def _get_worker_action(self, pos, assigned_tiles, target_pastures, farm, private, day, hour, inv, worker_idx, step, total_animals):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})
        seeds = private.get("seeds", {})
        is_shed_adj = tuple(pos) in SHED_ACCESS

        built_pastures = sum(1 for (px, py) in target_pastures if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) and isinstance(farm["tiles"][py][px], dict) and farm["tiles"][py][px].get("kind") == "PASTURE")
        if built_pastures < total_animals + 1:
            if (cx, cy) in target_pastures and current_tile is None:
                return ["BUILD_PASTURE"]
                for (px, py) in target_pastures:
                    if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                        t = farm["tiles"][py][px]
                        if t is None:
                            step_dir = get_step_towards((cx, cy), (px, py))
                            if step_dir: return [step_dir]

        for a_type in ["COW", "SHEEP"]:
            if inv.get(a_type, 0) > 0:
                if (cx, cy) in target_pastures and isinstance(current_tile, dict) and current_tile.get("kind") == "PASTURE" and "animal" not in current_tile:
                    return ["PLACE", a_type]
                for (px, py) in target_pastures:
                    if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                        t = farm["tiles"][py][px]
                        if isinstance(t, dict) and t.get("kind") == "PASTURE" and "animal" not in t:
                            step_dir = get_step_towards((cx, cy), (px, py))
                            if step_dir: return [step_dir]

        if is_shed_adj:
            for it in ["MILK", "WOOL", "STRAWBERRY", "MELON", "CARROT", "TOMATO", "EGG", "WHEAT"]:
                if inv.get(it, 0) > 0 and (it != "WHEAT" or inv.get("WHEAT", 0) > 3):
                    return ["PLACE", it, inv[it] - 3 if it == "WHEAT" else inv[it]]

            for a_type in ["COW", "SHEEP"]:
                if shed.get(a_type, 0) > 0 and inv.get(a_type, 0) == 0:
                    return ["PICKUP", a_type, 1]

            # Pickup fertilizer
            if shed.get("FERTILIZER", 0) > 0 and inv.get("FERTILIZER", 0) == 0:
                 return ["PICKUP", "FERTILIZER", min(5, shed.get("FERTILIZER", 0))]

            # Pickup wheat for feeding
            wheat_needed = min(3, shed.get("WHEAT", 0))
            if wheat_needed > 0 and inv.get("WHEAT", 0) == 0 and total_animals > 0:
                return ["PICKUP", "WHEAT", wheat_needed]

        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile.get("fed_today") and inv.get("WHEAT", 0) > 0: return ["FEED"]
            if not current_tile.get("cared_today"): return ["CARE"]
            if current_tile.get("fertilizer_available", False) and sum(inv.values()) < 100: return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0: return ["HARVEST"]

        # Assign first 3 workers to animal chores
        if worker_idx < 3:
            for (px, py) in target_pastures:
                if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and "animal" in t:
                        if (not t.get("fed_today") and inv.get("WHEAT", 0) > 0) or (not t.get("cared_today")) or (t.get("fertilizer_available", False) and sum(inv.values()) < 100) or t.get("yield_units", 0) > 0:
                            step_dir = get_step_towards((cx, cy), (px, py))
                            if step_dir: return [step_dir]

        # Crop Actions
        if current_tile != "LOCKED" and (cx, cy) not in target_pastures:
            if isinstance(current_tile, dict):
                kind = current_tile.get("kind")
                if kind == "WEED":
                    return ["DIG"]
                elif kind == "PLANT":
                    if not current_tile.get("watered_today"): return ["WATER"]
                    if current_tile.get("yield_units", 0) > 0: return ["HARVEST"]
                    # Apply fertilizer to Melons and Strawberries
                    if current_tile.get("crop") in ["STRAWBERRY", "MELON"] and current_tile.get("fertilized_until_day", -1) < day and inv.get("FERTILIZER", 0) > 0:
                        return ["FERTILIZE"]
            elif current_tile is None:
                if seeds.get("WHEAT", 0) > 0: return ["PLANT", "WHEAT"]
                if seeds.get("STRAWBERRY", 0) > 0: return ["PLANT", "STRAWBERRY"]
                if seeds.get("MELON", 0) > 0: return ["PLANT", "MELON"]

        # Move to assigned tiles
        for (px, py) in assigned_tiles:
            t = farm["tiles"][py][px]
            if t == "LOCKED": continue
            if t is None:
                if seeds.get("STRAWBERRY", 0) > 0 or seeds.get("MELON", 0) > 0 or seeds.get("WHEAT", 0) > 0:
                    step_dir = get_step_towards((cx, cy), (px, py))
                    if step_dir: return [step_dir]
            elif isinstance(t, dict):
                if t.get("kind") == "WEED":
                    step_dir = get_step_towards((cx, cy), (px, py))
                    if step_dir: return [step_dir]
                elif t.get("kind") == "PLANT":
                    if not t.get("watered_today") or t.get("yield_units", 0) > 0:
                            step_dir = get_step_towards((cx, cy), (px, py))
                            if step_dir: return [step_dir]

        # Move to shed if nothing else
        if not is_shed_adj:
            step_dir = get_step_towards((cx, cy), SHED_ACCESS[0])
            if step_dir: return [step_dir]

        return ["PASS"]

_agent_instance = AgentJules()
def agent(obs):
    return _agent_instance.act(obs)
