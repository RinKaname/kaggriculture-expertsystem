"""
Apex Ranch & Crop Grandmaster Engine:
Combines:
1. 4 Shed-Adjacent Pastures at (4,3), (4,2), (3,4), (3,3).
2. 2 Cows + 2 Sheep bought on Day 0-1, fed via Market Wheat ('BUY_PRODUCT', 'WHEAT', 4).
3. Daily Rancher Routine: PICKUP WHEAT -> FEED -> CARE -> COLLECT_FERTILIZER -> HARVEST -> DROP.
4. $100 Fertilizer Daily Harvest & Paced Sales.
5. High-Value Melons + Strawberries + Carrots on remaining 90+ tiles.
6. Disciplined 100-Tile Expansion: NE (Day 3-5), SW (Day 6-10), SE (Day 10-14).
"""
import math
from kaggle_environments import make

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "bonus_start": 2, "max_yield": 6, "base_price": 25},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "ongoing": False, "bonus_start": 2, "max_yield": 4, "base_price": 35},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "ongoing": True, "bonus_start": 0, "max_yield": 4, "interval": 1, "base_price": 60},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "bonus_start": 0, "max_yield": 4, "interval": 2, "base_price": 120},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "ongoing": False, "bonus_start": 6, "max_yield": 6, "base_price": 250},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
PASTURE_LOCS = [(4, 3), (4, 2), (3, 4), (3, 3)]


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


class ApexRanchAgent:
    def __init__(self):
        self.pasture_built = set()
        self.pasture_occupied = set()

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

        # Count active pastures & animals
        active_animals = 0
        for (px, py) in PASTURE_LOCS:
            t = farm["tiles"][py][px]
            if isinstance(t, dict) and "animal" in t:
                active_animals += 1

        needed_workers = max(1, math.ceil(num_tiles / 6.5)) + (1 if active_animals > 0 or day <= 2 else 0)
        target_hires = needed_workers - 1

        # --- Hour 0: Macro Economic Planning ---
        if hour == 0:
            # 1. Disciplined Land Expansion
            if unlocked_quads == 1 and money >= 1050 and day <= 5:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 2050 and day <= 11:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 3 and money >= 4050 and day <= 15:
                market_orders.append(["BUY_LAND"])

            # 2. Daily Animal Feed from Market
            if active_animals > 0:
                wheat_in_shed = shed.get("WHEAT", 0)
                wheat_to_buy = max(0, active_animals - wheat_in_shed)
                if wheat_to_buy > 0 and money >= wheat_to_buy * 30:
                    market_orders.append(["BUY_PRODUCT", "WHEAT", wheat_to_buy])

            # 3. Livestock Purchases on Day 0-2
            if day == 0 and money >= 1800:
                market_orders.append(["BUY_ANIMAL", "COW", 2])
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                market_orders.append(["BUY_PRODUCT", "WHEAT", 8])

            # 4. Worker Hires
            for _ in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 5. Capital & Crop Allocation
            land_reserved = 1000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 1) else (
                2000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 2) else (
                    4000 if ("BUY_LAND" in [o[0] for o in market_orders] and unlocked_quads == 3) else 0
                )
            )
            avail_money = money - land_reserved - 100

            # Crop tiles exclude pasture locations
            crop_tiles = [pos for pos in unlocked_tiles if pos not in PASTURE_LOCS]
            empty_count = sum(1 for (x, y) in crop_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(seeds.values())
            seeds_needed = max(0, empty_count - current_seeds)

            active_melons = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
            active_strawberries = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
            active_tomatoes = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "TOMATO")

            # High Value Melon Engine
            if day <= 16 and avail_money >= 160:
                melon_target = 35 if num_tiles >= 75 else (18 if num_tiles >= 50 else 8)
                if active_melons < melon_target:
                    melon_buy = min(seeds_needed, melon_target - active_melons, int((avail_money * 0.5) // 80))
                    if melon_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", melon_buy])
                        seeds_needed -= melon_buy
                        avail_money -= melon_buy * 80

            # Ongoing Strawberry Engine
            if day <= 14 and avail_money >= 200:
                straw_target = 15 if num_tiles >= 75 else 6
                if active_strawberries < straw_target:
                    straw_buy = min(seeds_needed, straw_target - active_strawberries, int((avail_money * 0.4) // 100))
                    if straw_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", straw_buy])
                        seeds_needed -= straw_buy
                        avail_money -= straw_buy * 100

            # Fast Turnover Carrots
            if day < 27 and seeds_needed > 0 and avail_money >= 20:
                carrot_buy = min(seeds_needed, int(avail_money // 20))
                if carrot_buy > 0 and len(market_orders) < 10:
                    market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                    seeds_needed -= carrot_buy
                    avail_money -= carrot_buy * 20

        # --- Quantitative Market Timing: Paced Selling ---
        total_shed_items = sum(shed.values())
        is_emergency_dump = (total_shed_items >= 80) or (day >= 28) or (money < 200 and day < 14)

        for item, count in shed.items():
            if count <= 0 or item not in PRODUCTS:
                continue
            if item in ["COW", "SHEEP", "GOOSE"]:
                continue

            cur_p = prices.get(item, 1)
            base_p = 100 if item == "FERTILIZER" else (160 if item == "MILK" else (200 if item == "WOOL" else CROPS.get(item, {}).get("base_price", 50)))
            
            # Fertilizer sells readily at $80+; Produce at >= 70% base
            thresh = 0.65 if item in ["FERTILIZER", "MILK", "WOOL"] else 0.70
            if is_emergency_dump or cur_p >= (base_p * thresh):
                sell_qty = count if is_emergency_dump else min(count, 4)
                if sell_qty > 0 and len(market_orders) < 10:
                    market_orders.append(["SELL", item, sell_qty])

        # --- Unit Dispatching: Dedicated Rancher + Crop Fleet ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        worker_actions = []

        # Worker 0 (Farmer) is our primary builder & rancher near shed
        farmer_pos = farm["farmer"]
        farmer_act = self._get_rancher_action(farmer_pos, farm, private, day, hour, private.get("inventories", [{}])[0])
        worker_actions.append(farmer_act)

        # Crop Fleet (Hands)
        crop_tiles = [pos for pos in unlocked_tiles if pos not in PASTURE_LOCS]
        sorted_crop_tiles = sorted(crop_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        num_hands = max(1, len(all_workers) - 1)
        chunk_size = max(1, math.ceil(len(sorted_crop_tiles) / num_hands))

        for h_idx, h_pos in enumerate(farm.get("hands", [])):
            inv = private.get("inventories", [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}])[h_idx + 1] if (h_idx + 1) < len(private.get("inventories", [])) else {}
            my_tiles = sorted_crop_tiles[h_idx * chunk_size : (h_idx + 1) * chunk_size]
            act = self._get_crop_worker_action(h_pos, my_tiles, farm, private, day, hour, inv)
            worker_actions.append(act)

        return {
            "farmer": worker_actions[0] if worker_actions else ["PASS"],
            "hands": worker_actions[1:] if len(worker_actions) > 1 else [],
            "market": market_orders[:10],
        }

    def _get_rancher_action(self, pos, farm, private, day, hour, inv):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})

        # 1. Build Pastures on Day 0-1
        for (px, py) in PASTURE_LOCS:
            t = farm["tiles"][py][px]
            if t is None:
                if (cx, cy) == (px, py):
                    return ["BUILD_PASTURE"]
                step = get_step_towards((cx, cy), (px, py))
                if step:
                    return [step]

        # 2. Place Animals into empty pastures
        for animal_type in ["COW", "SHEEP"]:
            if inv.get(animal_type, 0) > 0:
                for (px, py) in PASTURE_LOCS:
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and t.get("kind") == "PASTURE" and "animal" not in t:
                        if (cx, cy) == (px, py):
                            return ["PLACE", animal_type]
                        step = get_step_towards((cx, cy), (px, py))
                        if step:
                            return [step]
            elif shed.get(animal_type, 0) > 0 and (cx, cy) in [(4, 4), (4, 3), (3, 4)]:
                return ["PICKUP", animal_type, 1]

        # 3. Pickup Wheat from shed if needed for feeding
        unfed_count = sum(1 for (px, py) in PASTURE_LOCS if isinstance(farm["tiles"][py][px], dict) and "animal" in farm["tiles"][py][px] and not farm["tiles"][py][px]["fed_today"])
        if unfed_count > inv.get("WHEAT", 0) and shed.get("WHEAT", 0) > 0:
            if (cx, cy) in [(4, 4), (4, 3), (3, 4)]:
                pickup_qty = min(unfed_count - inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                if pickup_qty > 0:
                    return ["PICKUP", "WHEAT", pickup_qty]
            else:
                step = get_step_towards((cx, cy), (4, 4))
                if step:
                    return [step]

        # 4. Tend Animals in Pastures (FEED, CARE, COLLECT_FERTILIZER, HARVEST)
        # Check current tile first
        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile["fed_today"] and inv.get("WHEAT", 0) > 0:
                return ["FEED"]
            if not current_tile["cared_today"]:
                return ["CARE"]
            if current_tile.get("fertilizer_available", False):
                return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0:
                return ["HARVEST"]

        # Find next pasture that needs work
        for (px, py) in PASTURE_LOCS:
            t = farm["tiles"][py][px]
            if isinstance(t, dict) and "animal" in t:
                needs_feed = not t["fed_today"] and inv.get("WHEAT", 0) > 0
                needs_care = not t["cared_today"]
                needs_fert = t.get("fertilizer_available", False)
                needs_harvest = t.get("yield_units", 0) > 0
                if needs_feed or needs_care or needs_fert or needs_harvest:
                    step = get_step_towards((cx, cy), (px, py))
                    if step:
                        return [step]

        # 5. Drop collected goods (Fertilizer, Milk, Wool) to shed
        has_goods = any(inv.get(item, 0) > 0 for item in ["FERTILIZER", "MILK", "WOOL", "EGG", "CARROT", "MELON", "STRAWBERRY"])
        if has_goods:
            if (cx, cy) in [(4, 4), (4, 3), (3, 4)]:
                return ["DROP"]
            step = get_step_towards((cx, cy), (4, 4))
            if step:
                return [step]

        # 6. Idle near shed
        if (cx, cy) != (4, 3):
            step = get_step_towards((cx, cy), (4, 3))
            if step:
                return [step]

        return ["PASS"]

    def _get_crop_worker_action(self, pos, assigned_tiles, farm, private, day, hour, inv):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]

        # 1. Action on current tile
        if current_tile != "LOCKED" and (cx, cy) not in PASTURE_LOCS:
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
                for c in ["MELON", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # 2. Find next urgent tile in assigned chunk
        target_tile = None
        for (tx, ty) in assigned_tiles:
            if (tx, ty) in PASTURE_LOCS:
                continue
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


_agent_inst = None

def agent(obs):
    global _agent_inst
    if _agent_inst is None or obs.get("step", 0) == 0:
        _agent_inst = ApexRanchAgent()
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
    print(f"Average Apex Ranch Score: {sum(scores)/len(scores):,.2f}")
