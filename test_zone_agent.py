import math
from kaggle_environments import make

# --- Zone-based Agent Implementation ---

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


class FarmZoneAgent:
    def __init__(self):
        self.last_day = -1
        self.worker_targets = {}  # worker_idx -> list of (x, y) assigned tiles

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
        
        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        unlocked_quads = len(farm["unlocked_quadrants"])

        # Decide worker count needed: ~8-10 tiles per worker
        needed_workers = max(1, math.ceil(num_tiles / 9.0))
        target_hires = needed_workers - 1

        # --- Hour 0: Market Planning & Land Purchase ---
        if hour == 0:
            # 1. Check Land Expansion
            if unlocked_quads == 1 and money >= 1600 and day <= 21:
                market_orders.append(["BUY_LAND"])
            elif unlocked_quads == 2 and money >= 3500 and day <= 17:
                market_orders.append(["BUY_LAND"])

            # 2. Hires
            actual_hires = 0
            for h in range(target_hires):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])
                    actual_hires += 1

            # 3. Buy Seeds
            # Count empty tiles and current seed inventory
            empty_count = sum(1 for (x, y) in unlocked_tiles if farm["tiles"][y][x] is None)
            current_carrot_seeds = private.get("seeds", {}).get("CARROT", 0)
            current_wheat_seeds = private.get("seeds", {}).get("WHEAT", 0)
            current_melon_seeds = private.get("seeds", {}).get("MELON", 0)
            
            seeds_needed = max(0, empty_count - (current_carrot_seeds + current_wheat_seeds + current_melon_seeds))
            
            # Planting strategy:
            # If day <= 16 and day >= 1 and we have cash, plant some Melons
            avail_money = money - (1000 if "BUY_LAND" in [o[0] for o in market_orders] else 0) - 20
            
            if seeds_needed > 0 and avail_money > 20:
                # Late game (day >= 26): buy WHEAT (4 days) or CARROT (3 days)
                if day >= 27:
                    # Won't mature before day 30
                    pass
                elif day >= 26:
                    # 3 days left -> CARROT (2-3 days)
                    buy_count = min(seeds_needed, int(avail_money // 20))
                    if buy_count > 0:
                        market_orders.append(["BUY_SEED", "CARROT", buy_count])
                elif day <= 15 and avail_money >= 400 and day % 4 == 0:
                    # Buy batch of melons
                    melon_buy = min(seeds_needed, 4, int(avail_money // 80))
                    if melon_buy > 0:
                        market_orders.append(["BUY_SEED", "MELON", melon_buy])
                        seeds_needed -= melon_buy
                        avail_money -= melon_buy * 80
                    carrot_buy = min(seeds_needed, int(avail_money // 20))
                    if carrot_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                else:
                    carrot_buy = min(seeds_needed, int(avail_money // 20))
                    if carrot_buy > 0:
                        market_orders.append(["BUY_SEED", "CARROT", carrot_buy])
                    elif avail_money >= 10:
                        wheat_buy = min(seeds_needed, int(avail_money // 10))
                        if wheat_buy > 0:
                            market_orders.append(["BUY_SEED", "WHEAT", wheat_buy])

        # --- Continuous Market: Sell Shed Inventory ---
        shed = private.get("shed", {})
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS:
                if len(market_orders) < 10:
                    market_orders.append(["SELL", item, count])

        # --- Reactive Worker Dispatcher ---
        # Partition unlocked tiles snake-wise among all available workers
        all_workers_pos = [farm["farmer"]] + farm.get("hands", [])
        num_active_workers = len(all_workers_pos)

        # Sort unlocked tiles in snake order
        # For each row y: if y is even: x ascending, if y is odd: x descending
        sorted_tiles = sorted(unlocked_tiles, key=lambda p: (p[1], p[0] if p[1] % 2 == 0 else -p[0]))

        # Assign chunks of tiles to workers
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

        # 1. If currently standing on a tile that needs immediate action:
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
            elif current_tile is None:
                # Empty tile: check if we have seeds to plant
                seeds = private.get("seeds", {})
                for c in ["MELON", "CARROT", "WHEAT"]:
                    if seeds.get(c, 0) > 0:
                        return ["PLANT", c]

        # 2. Find the next tile in assigned_tiles that needs attention
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
            elif t is None:
                # Needs planting if seeds available
                seeds = private.get("seeds", {})
                if any(v > 0 for v in seeds.values()):
                    target_tile = (tx, ty)
                    break

        if target_tile is not None:
            step = get_step_towards((cx, cy), target_tile)
            if step:
                return [step]

        # 3. If all assigned tiles are attended, move towards the start of assigned tiles for next round
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
        agent_instance = FarmZoneAgent()
    return agent_instance.act(obs)


if __name__ == "__main__":
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
    env.run([agent, "starter"])
    print("Scores vs starter:", [(i, s.reward) for i, s in enumerate(env.steps[-1])])
