"""
Unified Apex Grandmaster Agent (130k Meta Architecture):
1. Pasture Ring Architecture:
   - Builds pastures around shed: (4,4), (4,3), (4,2), (3,4), (3,3), (2,4) in NW, and (5,4),(5,3),(6,3),(6,4),(7,4) in NE.
   - Buys 8 Cows + 6 Sheep progressively.
2. Market-Feed Arbitrage:
   - Buys WHEAT from market ('BUY_PRODUCT', 'WHEAT', n) to maintain shed feed buffer.
   - Sells harvested Fertilizer ($100 base) and Milk ($160 base) / Wool ($200 base).
3. Unified Worker Routine:
   - Worker spawns at shed (4,4) -> Picks up 2 Wheat.
   - Visits adjacent pastures on way out (FEED, CARE, COLLECT_FERTILIZER, HARVEST).
   - Radiates outward to assigned sector for crop WATER / HARVEST / PLANT (Strawberries & Melons).
   - Drops goods at shed (4,4) when returning or inventory full.
4. Guaranteed Land Expansion:
   - NE (Day 4-7), SW (Day 8-11), SE (Day 11-15).
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

NW_PASTURES = [(4, 4), (4, 3), (4, 2), (3, 4), (3, 3), (2, 4)]
NE_PASTURES = [(5, 4), (5, 3), (6, 3), (6, 4), (7, 4)]
SW_PASTURES = [(4, 5), (3, 5), (4, 6)]


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


class UnifiedApexAgent:
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
        return p

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
        unlocked_quads = farm["unlocked_quadrants"]
        
        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        target_pastures = self.get_target_pastures(unlocked_quads)

        # Count active animals
        active_animals = sum(1 for (px, py) in target_pastures if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) and isinstance(farm["tiles"][py][px], dict) and "animal" in farm["tiles"][py][px])
        
        # Scaling workforce
        needed_workers = max(4, math.ceil(num_tiles / 5.5) + math.ceil(active_animals / 2.0))
        target_hires = needed_workers - 1

        # --- Hour 0: Macro Economic Planning ---
        if hour == 0:
            # 1. Land Expansion
            if len(unlocked_quads) == 1 and money >= 1050 and day <= 7:
                market_orders.append(["BUY_LAND"])
            elif len(unlocked_quads) == 2 and money >= 2050 and day <= 11:
                market_orders.append(["BUY_LAND"])
            elif len(unlocked_quads) == 3 and money >= 4050 and day <= 15:
                market_orders.append(["BUY_LAND"])

            # 2. Worker Hires
            for _ in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

            # 3. Market Feed Refill for Animals
            if active_animals > 0:
                wheat_needed = max(0, (active_animals * 2) - shed.get("WHEAT", 0))
                if wheat_needed > 0 and money >= wheat_needed * 30 and len(market_orders) < 10:
                    market_orders.append(["BUY_PRODUCT", "WHEAT", wheat_needed])

            # 4. Animal Purchases
            if day == 0 and money >= 1800:
                market_orders.append(["BUY_ANIMAL", "COW", 2])
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                market_orders.append(["BUY_PRODUCT", "WHEAT", 10])
            elif day in [5, 8, 10] and money >= 1500 and active_animals < len(target_pastures):
                animal_type = "SHEEP" if active_animals % 2 == 1 else "COW"
                market_orders.append(["BUY_ANIMAL", animal_type, 1])

            # 5. Crop Allocation
            land_reserved = 1000 if ("BUY_LAND" in [o[0] for o in market_orders] and len(unlocked_quads) == 1) else (
                2000 if ("BUY_LAND" in [o[0] for o in market_orders] and len(unlocked_quads) == 2) else (
                    4000 if ("BUY_LAND" in [o[0] for o in market_orders] and len(unlocked_quads) == 3) else 0
                )
            )
            avail_money = money - land_reserved - 100

            crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
            empty_count = sum(1 for (x, y) in crop_tiles if farm["tiles"][y][x] is None)
            current_seeds = sum(seeds.values())
            seeds_needed = max(0, empty_count - current_seeds)

            active_strawberries = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
            active_melons = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")

            # Strawberry Matrix (Day 0 - 14)
            if day <= 14 and avail_money >= 200:
                straw_target = 30 if num_tiles >= 75 else (18 if num_tiles >= 50 else 8)
                if active_strawberries < straw_target:
                    straw_buy = min(seeds_needed, straw_target - active_strawberries, int((avail_money * 0.45) // 100))
                    if straw_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", straw_buy])
                        seeds_needed -= straw_buy
                        avail_money -= straw_buy * 100

            # Melon Engine (Day 0 - 16)
            if day <= 16 and avail_money >= 160:
                melon_target = 25 if num_tiles >= 75 else (15 if num_tiles >= 50 else 6)
                if active_melons < melon_target:
                    melon_buy = min(seeds_needed, melon_target - active_melons, int((avail_money * 0.45) // 80))
                    if melon_buy > 0 and len(market_orders) < 10:
                        market_orders.append(["BUY_SEED", "MELON", melon_buy])
                        seeds_needed -= melon_buy
                        avail_money -= melon_buy * 80

            # Fast Liquidity Carrots
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
            
            thresh = 0.60 if item in ["FERTILIZER", "MILK", "WOOL"] else 0.70
            if is_emergency_dump or cur_p >= (base_p * thresh):
                sell_qty = count if is_emergency_dump else min(count, 4)
                if sell_qty > 0 and len(market_orders) < 10:
                    market_orders.append(["SELL", item, sell_qty])

        # --- Spatial Multi-Worker Fleet ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
        sorted_crop_tiles = sorted(crop_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        chunk_size = max(1, math.ceil(len(sorted_crop_tiles) / max(1, num_active)))
        worker_actions = []

        inventories = private.get("inventories", [])
        for w_idx, w_pos in enumerate(all_workers):
            inv = inventories[w_idx] if w_idx < len(inventories) else {}
            my_tiles = sorted_crop_tiles[w_idx * chunk_size : (w_idx + 1) * chunk_size]
            act = self._get_worker_action(w_pos, my_tiles, target_pastures, farm, private, day, hour, inv, w_idx)
            worker_actions.append(act)

        farmer_act = worker_actions[0] if worker_actions else ["PASS"]
        hands_acts = worker_actions[1:] if len(worker_actions) > 1 else []

        return {
            "farmer": farmer_act,
            "hands": hands_acts,
            "market": market_orders[:10],
        }

    def _get_worker_action(self, pos, assigned_tiles, target_pastures, farm, private, day, hour, inv, worker_idx):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})

        # Phase 1: Build Pastures if standing on an empty target pasture tile
        if (cx, cy) in target_pastures and current_tile is None:
            return ["BUILD_PASTURE"]

        # Phase 2: Animal Placement if carrying an animal
        for a_type in ["COW", "SHEEP"]:
            if inv.get(a_type, 0) > 0:
                if (cx, cy) in target_pastures and isinstance(current_tile, dict) and current_tile.get("kind") == "PASTURE" and "animal" not in current_tile:
                    return ["PLACE", a_type]
                for (px, py) in target_pastures:
                    if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                        t = farm["tiles"][py][px]
                        if isinstance(t, dict) and t.get("kind") == "PASTURE" and "animal" not in t:
                            step = get_step_towards((cx, cy), (px, py))
                            if step:
                                return [step]

        # Phase 3: Pickup animal or wheat from shed when near shed
        if (cx, cy) in [(4, 4), (4, 3), (3, 4), (5, 4), (4, 5)]:
            for a_type in ["COW", "SHEEP"]:
                if shed.get(a_type, 0) > 0 and inv.get(a_type, 0) == 0:
                    return ["PICKUP", a_type, 1]
            if inv.get("WHEAT", 0) < 2 and shed.get("WHEAT", 0) > 0 and hour <= 8:
                qty = min(2 - inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                if qty > 0:
                    return ["PICKUP", "WHEAT", qty]

        # Phase 4: Animal Routine on current tile
        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile["fed_today"] and inv.get("WHEAT", 0) > 0:
                return ["FEED"]
            if not current_tile["cared_today"]:
                return ["CARE"]
            if current_tile.get("fertilizer_available", False):
                return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0:
                return ["HARVEST"]

        # Phase 5: Check if any adjacent/target pasture needs urgent tending and we are in morning (hour <= 12)
        if hour <= 12:
            for (px, py) in target_pastures:
                if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and "animal" in t:
                        if (not t["fed_today"] and inv.get("WHEAT", 0) > 0) or (not t["cared_today"]) or t.get("fertilizer_available", False) or t.get("yield_units", 0) > 0:
                            dist = abs(cx - px) + abs(cy - py)
                            if dist <= 3:
                                step = get_step_towards((cx, cy), (px, py))
                                if step:
                                    return [step]

        # Phase 6: Crop Action on current tile
        if current_tile != "LOCKED" and (cx, cy) not in target_pastures:
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
                for c in ["STRAWBERRY", "MELON", "CARROT", "TOMATO", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # Phase 7: Drop to Shed in evening (hour >= 18) or when inventory full
        total_held = sum(inv.values())
        has_produce = any(inv.get(it, 0) > 0 for it in ["MILK", "WOOL", "FERTILIZER", "STRAWBERRY", "MELON", "CARROT", "TOMATO"])
        if has_produce and (hour >= 18 or total_held >= 6):
            if (cx, cy) in [(4, 4), (4, 3), (3, 4), (5, 4), (4, 5)]:
                return ["DROP"]
            step = get_step_towards((cx, cy), (4, 4))
            if step:
                return [step]

        # Phase 8: Move to urgent crop tile in assigned sector
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

        # Phase 9: Build any unbuilt pasture if near one
        for (px, py) in target_pastures:
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                if farm["tiles"][py][px] is None:
                    step = get_step_towards((cx, cy), (px, py))
                    if step:
                        return [step]

        # Phase 10: Patrol home
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
        _agent_inst = UnifiedApexAgent()
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
    print(f"Average Unified Apex Score: {sum(scores)/len(scores):,.2f}")
