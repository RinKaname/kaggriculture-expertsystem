import math

# --- KAGGRICULTURE GAME CONSTANTS ---
CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "base_price": 25},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "ongoing": False, "base_price": 35},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "ongoing": True, "base_price": 60},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "base_price": 120},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 10, "ongoing": False, "base_price": 250}, # Age 10 max yield!
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

SELL_PRIORITY = {
    "MELON": 10, "WOOL": 9, "MILK": 8, "STRAWBERRY": 7,
    "FERTILIZER": 6, "CARROT": 5, "TOMATO": 4, "WHEAT": 3, "EGG": 2,
}

TOWN_SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

# 13 Pasture Layout (8 Cows + 5 Sheep)
NW_PASTURES = [(4, 4), (4, 3), (4, 2), (3, 4), (3, 3), (2, 4)]
NE_PASTURES = [(5, 4), (5, 3), (6, 3), (6, 4), (7, 4), (7, 3)]
SW_PASTURES = [(4, 5), (3, 5)]
SHED_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]


def get_step_towards(curr_pos, target_pos):
    cx, cy = curr_pos
    tx, ty = target_pos
    if cx < tx: return "EAST"
    if cx > tx: return "WEST"
    if cy < ty: return "SOUTH"
    if cy > ty: return "NORTH"
    return None


class UpgradedExpertAgent:
    def __init__(self):
        self.p = {
            # Economic thresholds
            "sell_thresh": 0.50,
            "milk_wool_thresh": 0.45,
            "sell_batch_size": 10,
            "shop_demand_thresh_mult": 0.80,
            
            # Crop targets
            "straw_target": 22,
            "melon_target": 16,
            "melon_cutoff_day": 14,
            "strawberry_start_day": 7,
            "fert_start_day": 5,

            # Livestock targets (8 Cows + 5 Sheep)
            "target_cows": 8,
            "target_sheep": 5,
            "animal_cutoff_day": 16,
            "animal_min_cash": 600,
            "feed_buffer_per_animal": 2,

            # Labor Scaling
            "max_workers": 12,
            "tiles_per_worker": 4.5,
            "hire_cutoff_hour": 5,

            # Land Expansion Days
            "quad2_day_cutoff": 7,  # NE ($1000)
            "quad3_day_cutoff": 11, # SW ($2000)
            
            "emergency_shed_cap": 65,
            "endgame_liquidation_day": 28
        }
        self.clone_confidence = 0

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

    def get_shop_demand(self, unlocked_shops):
        demand = {p: 0 for p in PRODUCTS}
        for shop in unlocked_shops:
            items = TOWN_SHOPS.get(shop, [])
            for it in items:
                multiplier = 2 if shop in ["YARN_STORE", "PET_CAFE"] else 1
                demand[it] += multiplier
        return demand

    def detect_clone(self, obs, step):
        if step in (4, 24, 48):
            farms = obs.get("farms", [])
            if len(farms) >= 2:
                my_p = obs.get("player", 0)
                opp_farm = farms[1 - my_p]
                hands = len(opp_farm.get("hands", []))
                quads = len(opp_farm.get("unlocked_quadrants", []))
                if hands >= 2 or quads >= 1:
                    self.clone_confidence = min(10, self.clone_confidence + 2)

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
        unlocked_shops = obs.get("town", {}).get("unlocked_shops", [])
        
        self.detect_clone(obs, step)
        shop_demand = self.get_shop_demand(unlocked_shops)

        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        target_pastures = self.get_target_pastures(unlocked_quads)

        # Count placed and owned animals
        placed_cows = sum(
            1 for (px, py) in target_pastures 
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) 
            and isinstance(farm["tiles"][py][px], dict) and farm["tiles"][py][px].get("animal") == "COW"
        )
        placed_sheep = sum(
            1 for (px, py) in target_pastures 
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) 
            and isinstance(farm["tiles"][py][px], dict) and farm["tiles"][py][px].get("animal") == "SHEEP"
        )
        total_cows = placed_cows + shed.get("COW", 0) + sum(inv.get("COW", 0) for inv in inventories)
        total_sheep = placed_sheep + shed.get("SHEEP", 0) + sum(inv.get("SHEEP", 0) for inv in inventories)
        total_animals = total_cows + total_sheep

        # --- 1. Continuous & Front-Running Market Selling ---
        total_shed_items = sum(shed.values())
        is_emergency_dump = (total_shed_items >= self.p["emergency_shed_cap"]) or (day >= self.p["endgame_liquidation_day"]) or (money < 200 and day < 12)

        potential_sells = []
        for item, count in shed.items():
            if count <= 0 or item not in PRODUCTS:
                continue
            if item in ["COW", "SHEEP", "GOOSE"]:
                continue

            cur_p = prices.get(item, 1)
            base_p = 100 if item == "FERTILIZER" else (160 if item == "MILK" else (200 if item == "WOOL" else CROPS.get(item, {}).get("base_price", 50)))
            
            thresh = 0.35 if (item == "FERTILIZER" or day < 8) else (self.p["milk_wool_thresh"] if item in ["MILK", "WOOL"] else self.p["sell_thresh"])
            
            if shop_demand.get(item, 0) > 0:
                thresh *= self.p["shop_demand_thresh_mult"]

            # Front-run clone dumps
            if self.clone_confidence >= 2 and item in ["MELON", "STRAWBERRY", "MILK", "WOOL"]:
                thresh *= 0.85

            if is_emergency_dump or cur_p >= (base_p * thresh):
                sell_qty = count if (is_emergency_dump or item in ["FERTILIZER", "MELON", "STRAWBERRY"] or day >= 27) else min(count, self.p["sell_batch_size"])
                if sell_qty > 0:
                    total_val = cur_p * sell_qty
                    p_tie = SELL_PRIORITY.get(item, 0)
                    potential_sells.append((total_val, cur_p, p_tie, item, sell_qty))

        potential_sells.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        for _, _, _, item, qty in potential_sells:
            if len(market_orders) < 10:
                market_orders.append(["SELL", item, qty])

        # --- 2. Dynamic Land Expansion (NE -> SW) ---
        if len(unlocked_quads) == 1 and money >= 1050 and day <= self.p["quad2_day_cutoff"] and len(market_orders) < 10:
            market_orders.append(["BUY_LAND"])
        elif len(unlocked_quads) == 2 and money >= 2050 and day <= self.p["quad3_day_cutoff"] and len(market_orders) < 10:
            market_orders.append(["BUY_LAND"])

        # --- 3. Worker Fleet Scaling (Fibonacci Region Up to 12) ---
        target_fleet = 4 if day < 4 else (6 if day < 8 else min(self.p["max_workers"], max(6, math.ceil(num_tiles / self.p["tiles_per_worker"]))))
        current_workers = 1 + len(farm.get("hands", []))
        if current_workers < target_fleet and hour <= self.p["hire_cutoff_hour"] and money >= 15:
            hires_to_make = min(2, target_fleet - current_workers)
            for _ in range(hires_to_make):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

        # --- 4. Animal Feed Buffer ---
        if (placed_cows + placed_sheep) > 0:
            wheat_in_shed = shed.get("WHEAT", 0)
            wheat_needed = ((placed_cows + placed_sheep) * self.p["feed_buffer_per_animal"]) - wheat_in_shed
            if wheat_needed > 0 and money >= wheat_needed * 30 and len(market_orders) < 10:
                buy_amt = min(wheat_needed, 8)
                market_orders.append(["BUY_PRODUCT", "WHEAT", buy_amt])

        # --- 5. Livestock Scaling (8 Cows + 5 Sheep) ---
        max_target_animals = 3 if len(unlocked_quads) == 1 else (8 if len(unlocked_quads) == 2 else 13)
        if total_animals < max_target_animals and day <= self.p["animal_cutoff_day"] and money >= self.p["animal_min_cash"]:
            if total_cows < self.p["target_cows"]:
                a_type = "COW"
            elif total_sheep < self.p["target_sheep"]:
                a_type = "SHEEP"
            else:
                a_type = "SHEEP" if total_sheep <= total_cows else "COW"

            if len(market_orders) < 10 and (shed.get(a_type, 0) == 0):
                market_orders.append(["BUY_ANIMAL", a_type, 1])

        # --- 6. Seed Economy & Crop Matrix ---
        crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
        active_strawberries = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
        active_melons = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
        held_straw_seeds = seeds.get("STRAWBERRY", 0)
        held_melon_seeds = seeds.get("MELON", 0)

        safety_margin = 150 + (1000 if len(unlocked_quads) == 1 and day >= 5 else (2000 if len(unlocked_quads) == 2 and day >= 9 else 0))
        spendable_money = max(0, money - safety_margin)

        # Strawberry Matrix
        straw_target_cap = self.p["straw_target"] if num_tiles >= 75 else (14 if num_tiles >= 50 else 4)
        if self.p["strawberry_start_day"] <= day <= 18 and (active_strawberries + held_straw_seeds) < straw_target_cap and spendable_money >= 100:
            s_buy = min(straw_target_cap - (active_strawberries + held_straw_seeds), 4, int(spendable_money // 100))
            if s_buy > 0 and len(market_orders) < 10:
                market_orders.append(["BUY_SEED", "STRAWBERRY", s_buy])
                spendable_money -= s_buy * 100

        # Melon Matrix
        melon_target_cap = self.p["melon_target"] if num_tiles >= 75 else 12
        if day <= self.p["melon_cutoff_day"] and (active_melons + held_melon_seeds) < melon_target_cap and spendable_money >= 80:
            m_buy = min(melon_target_cap - (active_melons + held_melon_seeds), 4, int(spendable_money // 80))
            if m_buy > 0 and len(market_orders) < 10:
                market_orders.append(["BUY_SEED", "MELON", m_buy])
                spendable_money -= m_buy * 80

        # Supporting Wheat
        empty_crop_tiles = sum(1 for (x, y) in crop_tiles if farm["tiles"][y][x] is None)
        total_seeds_held = sum(seeds.values())
        if day < 27 and empty_crop_tiles > total_seeds_held and spendable_money >= 10:
            w_buy = min(empty_crop_tiles - total_seeds_held, 8, int(spendable_money // 10))
            if w_buy > 0 and len(market_orders) < 10:
                market_orders.append(["BUY_SEED", "WHEAT", w_buy])

        # --- Spatial Multi-Worker Dispatch ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        num_active = len(all_workers)

        sorted_crop_tiles = sorted(crop_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))
        chunk_size = max(1, math.ceil(len(sorted_crop_tiles) / max(1, num_active)))
        worker_actions = []

        for w_idx, w_pos in enumerate(all_workers):
            inv = inventories[w_idx] if w_idx < len(inventories) else {}
            my_tiles = sorted_crop_tiles[w_idx * chunk_size : (w_idx + 1) * chunk_size]
            act = self._get_worker_action(w_pos, my_tiles, target_pastures, farm, private, day, hour, inv, w_idx)
            worker_actions.append(act)

        return {
            "farmer": worker_actions[0] if worker_actions else ["PASS"],
            "hands": worker_actions[1:] if len(worker_actions) > 1 else [],
            "market": market_orders[:10],
        }

    def _get_worker_action(self, pos, assigned_tiles, target_pastures, farm, private, day, hour, inv, worker_idx):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})
        is_shed_adj = tuple(pos) in SHED_ACCESS

        # Build pasture if on empty pasture tile
        if (cx, cy) in target_pastures and current_tile is None:
            return ["BUILD_PASTURE"]

        # Place animal if holding one
        for a_type in ["COW", "SHEEP"]:
            if inv.get(a_type, 0) > 0:
                if (cx, cy) in target_pastures and isinstance(current_tile, dict) and current_tile.get("kind") == "PASTURE" and "animal" not in current_tile:
                    return ["PLACE", a_type]
                for (px, py) in target_pastures:
                    if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                        t = farm["tiles"][py][px]
                        if isinstance(t, dict) and t.get("kind") == "PASTURE" and "animal" not in t:
                            step = get_step_towards((cx, cy), (px, py))
                            if step: return [step]

        # Shed Drop & Pickup
        if is_shed_adj:
            # 1-turn instantaneous DROP for all carried produce/fertilizer
            carried_produce = sum(inv.get(it, 0) for it in ["MILK", "WOOL", "FERTILIZER", "STRAWBERRY", "MELON", "CARROT", "TOMATO"])
            if carried_produce > 0 or inv.get("WHEAT", 0) > 4:
                return ["DROP"]
            
            for a_type in ["COW", "SHEEP"]:
                if shed.get(a_type, 0) > 0 and inv.get(a_type, 0) == 0:
                    return ["PICKUP", a_type, 1]
            if inv.get("WHEAT", 0) < 3 and shed.get("WHEAT", 0) > 0 and hour <= 12:
                qty = min(3 - inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                if qty > 0: return ["PICKUP", "WHEAT", qty]

        # On Animal Tile Actions
        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile["fed_today"] and inv.get("WHEAT", 0) > 0: return ["FEED"]
            if not current_tile["cared_today"]: return ["CARE"]
            if current_tile.get("fertilizer_available", False): return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0: return ["HARVEST"]

        # Morning Pasture Sweep for dedicated animal keepers (first 3 workers)
        if hour <= 12 and worker_idx in [0, 1, 2]:
            for (px, py) in target_pastures:
                if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and "animal" in t:
                        if (not t["fed_today"] and inv.get("WHEAT", 0) > 0) or (not t["cared_today"]) or t.get("fertilizer_available", False) or t.get("yield_units", 0) > 0:
                            step = get_step_towards((cx, cy), (px, py))
                            if step: return [step]

        # On Plant / Crop Tile Actions
        if current_tile != "LOCKED" and (cx, cy) not in target_pastures:
            if isinstance(current_tile, dict):
                kind = current_tile.get("kind")
                if kind == "WEED": return ["DIG"]
                elif kind == "PLANT":
                    crop = current_tile["crop"]
                    cd = CROPS[crop]
                    age = day - current_tile["planted_day"]
                    should_harvest = False
                    if cd["ongoing"]:
                        if current_tile.get("yield_units", 0) > 0: should_harvest = True
                    else:
                        # MELON max yield is AGE 10!
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]):
                            should_harvest = True
                    
                    if should_harvest: return ["HARVEST"]
                    if day >= self.p["fert_start_day"] and inv.get("FERTILIZER", 0) > 0 and crop in ["STRAWBERRY", "MELON"]:
                        if current_tile.get("fertilized_until_day", 0) <= day: return ["FERTILIZE"]
                    if not current_tile.get("watered_today", False): return ["WATER"]
            
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "MELON", "WHEAT", "CARROT", "TOMATO"]:
                    if seeds.get(c, 0) > 0: return ["PLANT", c]

        # Return to Shed if carrying heavy yield
        has_produce = any(inv.get(it, 0) > 0 for it in ["MILK", "WOOL", "FERTILIZER", "STRAWBERRY", "MELON", "CARROT", "TOMATO"])
        if has_produce and (hour >= 16 or sum(inv.values()) >= 4):
            closest_shed = min(SHED_ACCESS, key=lambda s_pos: abs(cx - s_pos[0]) + abs(cy - s_pos[1]))
            step = get_step_towards((cx, cy), closest_shed)
            if step: return [step]

        # Navigate to assigned crop tasks
        target_tile = None
        for (tx, ty) in assigned_tiles:
            t = farm["tiles"][ty][tx]
            if t == "LOCKED": continue
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
                        if t.get("yield_units", 0) > 0: should_harvest = True
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
            if step: return [step]

        # Unbuilt Pastures navigation
        for (px, py) in target_pastures:
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                if farm["tiles"][py][px] is None:
                    step = get_step_towards((cx, cy), (px, py))
                    if step: return [step]

        if assigned_tiles:
            home = assigned_tiles[0]
            if (cx, cy) != home:
                step = get_step_towards((cx, cy), home)
                if step: return [step]

        return ["PASS"]


_player_agents = {}

def agent(obs):
    global _player_agents
    p_id = obs.get("player", 0)
    if obs.get("step", 0) == 0 or p_id not in _player_agents:
        _player_agents[p_id] = UpgradedExpertAgent()
    return _player_agents[p_id].act(obs)
