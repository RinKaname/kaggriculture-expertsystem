import math
from collections import deque, defaultdict

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "base_price": 25},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "ongoing": False, "base_price": 35},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "ongoing": True, "base_price": 60},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "base_price": 120},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "ongoing": False, "base_price": 250},
}

PRODUCTS_BASE_PRICES = {
    "WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
    "EGG": 40, "MILK": 160, "WOOL": 200, "FERTILIZER": 100
}

# Grid Layout Presets for Pastures and Coops around Shed
NW_PASTURES = [(4, 4), (4, 3), (4, 2), (3, 4), (3, 3)]
NW_COOPS = [(2, 4), (2, 3)]
NE_PASTURES = [(5, 4), (5, 3), (6, 3), (6, 4)]
NE_COOPS = [(7, 4), (7, 3)]
SW_PASTURES = [(4, 5), (3, 5), (4, 6)]


def get_bfs_step(curr_pos, target_pos, farm_tiles):
    """BFS shortest pathfinder on 10x10 grid avoiding locked tiles."""
    if curr_pos == target_pos:
        return None

    board_size = len(farm_tiles)
    queue = deque([(curr_pos, [])])
    visited = {curr_pos}
    dirs = [("NORTH", (0, -1)), ("SOUTH", (0, 1)), ("EAST", (1, 0)), ("WEST", (-1, 0))]

    while queue:
        (cx, cy), path = queue.popleft()
        if (cx, cy) == target_pos:
            return path[0] if path else None

        for move, (dx, dy) in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < board_size and 0 <= ny < board_size:
                if farm_tiles[ny][nx] != "LOCKED" and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [move]))
    return None


class ZScoreMarketTracker:
    """Rolling window market analyzer to sell during spikes and hold during dips."""
    def __init__(self, window=24):
        self.price_history = defaultdict(list)
        self.window = window

    def update(self, current_prices):
        for item, price in current_prices.items():
            self.price_history[item].append(price)
            if len(self.price_history[item]) > self.window:
                self.price_history[item].pop(0)

    def should_sell(self, item, current_price, day, shed_count):
        # Never sell fertilizer or animals
        if item in ["FERTILIZER", "COW", "SHEEP", "GOOSE"]:
            return False

        base = PRODUCTS_BASE_PRICES.get(item, 50)
        # End game or shed capacity emergency
        if day >= 28 or shed_count >= 75:
            return True

        hist = self.price_history[item]
        if len(hist) < 5:
            return current_price >= base * 0.85

        mean = sum(hist) / len(hist)
        std = (sum((p - mean) ** 2 for p in hist) / len(hist)) ** 0.5
        z_score = (current_price - mean) / (std + 1e-3)

        return z_score >= 0.5 or current_price >= base * 0.90


class ApexGrandmasterAgent:
    def __init__(self):
        self.market_tracker = ZScoreMarketTracker()

    def get_unlocked_tiles(self, farm):
        tiles = []
        board_size = len(farm["tiles"])
        for y in range(board_size):
            for x in range(board_size):
                if farm["tiles"][y][x] != "LOCKED":
                    tiles.append((x, y))
        return tiles

    def get_shed_access(self, farm):
        shed_pos = farm.get("shed_position", (4, 4))
        sx, sy = shed_pos if isinstance(shed_pos, (tuple, list)) else (4, 4)
        access = []
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            access.append((sx + dx, sy + dy))
        return access

    def get_target_structures(self, unlocked_quads):
        pastures = list(NW_PASTURES)
        coops = list(NW_COOPS)
        if "NE" in unlocked_quads:
            pastures += NE_PASTURES
            coops += NE_COOPS
        if "SW" in unlocked_quads:
            pastures += SW_PASTURES
        return pastures, coops

    def act(self, obs):
        player_id = obs["player"]
        farm = obs["farms"][player_id]
        private = obs["private"]
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        money = farm["money"]
        shed = private.get("shed", {})
        seeds = private.get("seeds", {})
        inventories = private.get("inventories", [])
        market_info = obs.get("market", {})
        prices = market_info.get("prices", {})
        unlocked_quads = farm.get("unlocked_quadrants", ["NW"])

        self.market_tracker.update(prices)

        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        target_pastures, target_coops = self.get_target_structures(unlocked_quads)
        shed_access = self.get_shed_access(farm)

        # Count active livestock
        placed_pasture_animals = sum(1 for (px, py) in target_pastures if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) and isinstance(farm["tiles"][py][px], dict) and "animal" in farm["tiles"][py][px])
        placed_coop_animals = sum(1 for (cx, cy) in target_coops if cx < len(farm["tiles"][0]) and cy < len(farm["tiles"]) and isinstance(farm["tiles"][cy][cx], dict) and "animal" in farm["tiles"][cy][cx])
        total_animals = placed_pasture_animals + placed_coop_animals + sum(shed.get(a, 0) for a in ["COW", "SHEEP", "GOOSE"])

        # --- Priority Order Queue Construction ---
        buy_orders = []
        sell_orders = []

        # 1. Land Expansion (Early Aggressive Unlocking)
        if len(unlocked_quads) == 1 and money >= 1050 and day <= 6:
            buy_orders.append(["BUY_LAND"])
        elif len(unlocked_quads) == 2 and money >= 2050 and day <= 10:
            buy_orders.append(["BUY_LAND"])
        elif len(unlocked_quads) == 3 and money >= 4100 and day <= 14:
            buy_orders.append(["BUY_LAND"])

        # 2. Worker Fleet Scaling
        needed_workers = min(18, max(5, math.ceil(num_tiles / 5.0) + (2 if total_animals > 0 else 0)))
        current_workers = 1 + len(farm.get("hands", []))
        if current_workers < needed_workers and hour <= 4 and money >= 10:
            buy_orders.append(["HIRE"])

        # 3. Livestock Engine Purchases (Cows + Geese)
        max_target_animals = 4 if len(unlocked_quads) == 1 else (10 if len(unlocked_quads) == 2 else 14)
        if total_animals < max_target_animals and money >= 500 and day <= 16:
            a_type = "GOOSE" if (total_animals % 3 == 0) else ("SHEEP" if total_animals % 2 == 1 else "COW")
            if shed.get(a_type, 0) == 0:
                buy_orders.append(["BUY_ANIMAL", a_type, 1])

        # 4. Crop Seeds & Internal Feed Rotation
        crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures and pos not in target_coops]
        active_strawberries = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
        active_melons = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
        active_wheat = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "WHEAT")

        spendable_money = max(0, money - 150)

        # Internal Wheat Patch Guarantee (3-4 tiles for $1.67 feed vs $30 market overpay)
        if active_wheat + seeds.get("WHEAT", 0) < 4 and spendable_money >= 10 and day < 27:
            w_buy = min(4 - (active_wheat + seeds.get("WHEAT", 0)), 4)
            buy_orders.append(["BUY_SEED", "WHEAT", w_buy])
            spendable_money -= w_buy * 10

        # Strawberry Matrix Target
        straw_target = 35 if num_tiles >= 75 else (15 if num_tiles >= 50 else 4)
        if 4 <= day <= 18 and (active_strawberries + seeds.get("STRAWBERRY", 0)) < straw_target and spendable_money >= 100:
            s_buy = min(straw_target - (active_strawberries + seeds.get("STRAWBERRY", 0)), 4, int(spendable_money // 100))
            if s_buy > 0:
                buy_orders.append(["BUY_SEED", "STRAWBERRY", s_buy])
                spendable_money -= s_buy * 100

        # Melon Engine Target
        melon_target = 12 if num_tiles <= 50 else 16
        if day <= 18 and (active_melons + seeds.get("MELON", 0)) < melon_target and spendable_money >= 80:
            m_buy = min(melon_target - (active_melons + seeds.get("MELON", 0)), 4, int(spendable_money // 80))
            if m_buy > 0:
                buy_orders.append(["BUY_SEED", "MELON", m_buy])

        # 5. Market Sales Execution (Z-Score Filtered)
        total_shed_items = sum(shed.values())
        for item, count in shed.items():
            if count <= 0:
                continue
            cur_p = prices.get(item, 1)
            if self.market_tracker.should_sell(item, cur_p, day, total_shed_items):
                sell_orders.append(["SELL", item, min(count, 5)])

        # Prioritize Buys over Sells so crucial upgrades are never truncated!
        market_orders = (buy_orders + sell_orders)[:10]

        # --- Worker Action Generation ---
        all_workers = [farm["farmer"]] + farm.get("hands", [])
        worker_actions = []

        for w_idx, w_pos in enumerate(all_workers):
            inv = inventories[w_idx] if w_idx < len(inventories) else {}
            act = self._get_worker_action(w_pos, crop_tiles, target_pastures, target_coops, shed_access, farm, private, day, hour, inv, w_idx)
            worker_actions.append(act)

        return {
            "farmer": worker_actions[0] if worker_actions else ["PASS"],
            "hands": worker_actions[1:] if len(worker_actions) > 1 else [],
            "market": market_orders,
        }

    def _get_worker_action(self, pos, crop_tiles, target_pastures, target_coops, shed_access, farm, private, day, hour, inv, worker_idx):
        cx, cy = pos
        current_tile = farm["tiles"][cy][cx]
        shed = private.get("shed", {})
        is_shed_adj = tuple(pos) in shed_access

        # Phase 1: Structure Building
        if (cx, cy) in target_pastures and current_tile is None:
            return ["BUILD_PASTURE"]
        if (cx, cy) in target_coops and current_tile is None:
            return ["BUILD_COOP"]

        # Phase 2: Animal Placement
        for a_type in ["COW", "SHEEP", "GOOSE"]:
            if inv.get(a_type, 0) > 0:
                target_list = target_coops if a_type == "GOOSE" else target_pastures
                kind_req = "COOP" if a_type == "GOOSE" else "PASTURE"
                if (cx, cy) in target_list and isinstance(current_tile, dict) and current_tile.get("kind") == kind_req and "animal" not in current_tile:
                    return ["PLACE", a_type]
                for (px, py) in target_list:
                    if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                        t = farm["tiles"][py][px]
                        if isinstance(t, dict) and t.get("kind") == kind_req and "animal" not in t:
                            step = get_bfs_step((cx, cy), (px, py), farm["tiles"])
                            if step:
                                return [step]

        # Phase 3: Shed Operations (Deposit Goods & Refill Supplies)
        if is_shed_adj:
            # Deposit harvested produce
            for it in ["MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "CARROT", "TOMATO", "WHEAT"]:
                if inv.get(it, 0) > 0 and (it != "WHEAT" or inv.get("WHEAT", 0) > 3):
                    return ["PLACE", it, inv[it]]

            # Deposit excess fertilizer if carrying > 2
            if inv.get("FERTILIZER", 0) > 2:
                return ["PLACE", "FERTILIZER", inv["FERTILIZER"] - 1]

            # Pickup animals from shed
            for a_type in ["COW", "SHEEP", "GOOSE"]:
                if shed.get(a_type, 0) > 0 and inv.get(a_type, 0) == 0:
                    return ["PICKUP", a_type, 1]

            # Pickup Wheat Feed for animal handlers (Hands 1 & 2)
            if worker_idx in [1, 2] and inv.get("WHEAT", 0) < 3 and shed.get("WHEAT", 0) > 0:
                qty = min(3 - inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                if qty > 0:
                    return ["PICKUP", "WHEAT", qty]

            # Pickup Fertilizer for crop specialists / Farmer
            if worker_idx not in [1, 2] and inv.get("FERTILIZER", 0) == 0 and shed.get("FERTILIZER", 0) > 0:
                return ["PICKUP", "FERTILIZER", min(2, shed.get("FERTILIZER", 0))]

        # Phase 4: Animal Routine on current tile
        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile.get("fed_today", True) and inv.get("WHEAT", 0) > 0:
                return ["FEED"]
            if not current_tile.get("cared_today", False):
                return ["CARE"]
            if current_tile.get("fertilizer_available", False):
                return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0:
                return ["HARVEST"]

        # Phase 5: Morning Pasture/Coop Sweep (Hands 1 & 2)
        if worker_idx in [1, 2]:
            all_animal_structures = target_pastures + target_coops
            for (px, py) in all_animal_structures:
                if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and "animal" in t:
                        if (not t.get("fed_today", True) and inv.get("WHEAT", 0) > 0) or (not t.get("cared_today", False)) or t.get("fertilizer_available", False) or t.get("yield_units", 0) > 0:
                            step = get_bfs_step((cx, cy), (px, py), farm["tiles"])
                            if step:
                                return [step]

        # Phase 6: Crop Action on current tile
        if current_tile != "LOCKED" and (cx, cy) not in target_pastures and (cx, cy) not in target_coops:
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

                    # Apply Fertilizer to Melons (Days 6-12) & Strawberries
                    if inv.get("FERTILIZER", 0) > 0 and crop in ["MELON", "STRAWBERRY"]:
                        if current_tile.get("fertilized_until_day", 0) <= day:
                            if crop == "MELON" and 6 <= day <= 12:
                                return ["FERTILIZE"]
                            elif crop == "STRAWBERRY":
                                return ["FERTILIZE"]

                    # Sacred Melon / Crop Watering
                    if not current_tile.get("watered_today", False):
                        return ["WATER"]

            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "MELON", "WHEAT", "CARROT", "TOMATO"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # Phase 7: Deposit Goods to Shed
        has_goods = any(inv.get(it, 0) > 0 for it in ["MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "CARROT", "TOMATO"])
        if has_goods and (hour >= 17 or sum(inv.values()) >= 4):
            closest_shed = min(shed_access, key=lambda s: abs(cx - s[0]) + abs(cy - s[1]))
            step = get_bfs_step((cx, cy), closest_shed, farm["tiles"])
            if step:
                return [step]

        # Phase 8: Move to Urgent Crop Task via BFS
        for (tx, ty) in crop_tiles:
            t = farm["tiles"][ty][tx]
            if t == "LOCKED":
                continue
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "WEED":
                    step = get_bfs_step((cx, cy), (tx, ty), farm["tiles"])
                    if step:
                        return [step]
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
                        step = get_bfs_step((cx, cy), (tx, ty), farm["tiles"])
                        if step:
                            return [step]

        return ["PASS"]


_player_agents = {}

def agent(obs):
    global _player_agents
    p_id = obs.get("player", 0)
    if obs.get("step", 0) == 0 or p_id not in _player_agents:
        _player_agents[p_id] = ApexGrandmasterAgent()
    return _player_agents[p_id].act(obs)