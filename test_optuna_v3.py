import math
import multiprocessing
import optuna
from tqdm import tqdm
from kaggle_environments import make

# --- OFFICIAL KAGGRICULTURE GAME CONSTANTS ---
CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "ongoing": False, "base_price": 25},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "ongoing": False, "base_price": 35},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "ongoing": True, "base_price": 60},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "ongoing": True, "base_price": 120},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "ongoing": False, "base_price": 250},
}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]

# Exact shop demand mappings from official environment:
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

NW_PASTURES = [(4, 4), (4, 3), (4, 2), (3, 4), (3, 3), (2, 4)]
NE_PASTURES = [(5, 4), (5, 3), (6, 3), (6, 4), (7, 4), (7, 3)]
SW_PASTURES = [(4, 5), (3, 5), (4, 6)]
SHED_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]


def get_step_towards(curr_pos, target_pos):
    cx, cy = curr_pos
    tx, ty = target_pos
    if cx < tx: return "EAST"
    if cx > tx: return "WEST"
    if cy < ty: return "SOUTH"
    if cy > ty: return "NORTH"
    return None


# --- ZERO-BUG ADAPTIVE APEX GRANDMASTER AGENT ---
class AdaptiveApexAgent:
    def __init__(self, params):
        self.p = params

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
                # Single-product shops consume 2x in the engine
                multiplier = 2 if shop in ["YARN_STORE", "PET_CAFE"] else 1
                demand[it] += multiplier
        return demand

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
        
        shop_demand = self.get_shop_demand(unlocked_shops)

        market_orders = []
        unlocked_tiles = self.get_unlocked_tiles(farm)
        num_tiles = len(unlocked_tiles)
        target_pastures = self.get_target_pastures(unlocked_quads)

        placed_animals = sum(
            1 for (px, py) in target_pastures 
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]) 
            and isinstance(farm["tiles"][py][px], dict) and "animal" in farm["tiles"][py][px]
        )
        shed_animals = shed.get("COW", 0) + shed.get("SHEEP", 0)
        inv_animals = sum(inv.get("COW", 0) + inv.get("SHEEP", 0) for inv in inventories)
        total_animals = placed_animals + shed_animals + inv_animals

        # --- Priority 1: Land Expansion ---
        if len(unlocked_quads) == 1 and money >= 1050 and day <= self.p["quad2_day_cutoff"] and len(market_orders) < 10:
            market_orders.append(["BUY_LAND"])
        elif len(unlocked_quads) == 2 and money >= 2050 and day <= self.p["quad3_day_cutoff"] and len(market_orders) < 10:
            market_orders.append(["BUY_LAND"])
        elif self.p["quad4_enable"] and len(unlocked_quads) == 3 and money >= 4100 and day <= 20 and len(market_orders) < 10:
            market_orders.append(["BUY_LAND"])

        # --- Priority 2: Worker Hiring ---
        base_needed = max(5, math.ceil(num_tiles / self.p["tiles_per_worker"]) + (2 if placed_animals > 0 else 0))
        late_surge = self.p["late_worker_surge"] if (day >= 20 and money >= 2000) else 0
        needed_workers = min(18, base_needed + late_surge)

        current_workers = 1 + len(farm.get("hands", []))
        if current_workers < needed_workers and hour <= self.p["hire_cutoff_hour"] and money >= 10:
            hires_to_make = min(2, needed_workers - current_workers)
            for _ in range(hires_to_make):
                if len(market_orders) < 10:
                    market_orders.append(["HIRE"])

        # --- Priority 3: Animal Feed Buffer (Prevent Animal Loss) ---
        if placed_animals > 0:
            wheat_in_shed = shed.get("WHEAT", 0)
            wheat_needed = (placed_animals * self.p["feed_buffer_per_animal"]) - wheat_in_shed
            if wheat_needed > 0 and money >= wheat_needed * 30 and len(market_orders) < 10:
                buy_amt = min(wheat_needed, 8)
                market_orders.append(["BUY_PRODUCT", "WHEAT", buy_amt])

        # --- Priority 4: Livestock Scaling & Purchase ---
        max_target_animals = 4 if len(unlocked_quads) == 1 else (self.p["max_animals_quad2"] if len(unlocked_quads) == 2 else 14)
        if total_animals < max_target_animals and money >= self.p["animal_min_cash"] and day <= self.p["animal_cutoff_day"]:
            # Wool has higher demand if Yarn Store is unlocked
            if shop_demand.get("WOOL", 0) > 0:
                a_type = "SHEEP" if (total_animals % 3 != 0) else "COW"
            else:
                a_type = "SHEEP" if (total_animals % 2 == 1) else "COW"

            if len(market_orders) < 10 and (shed.get(a_type, 0) == 0):
                market_orders.append(["BUY_ANIMAL", a_type, 1])

        # --- Priority 5: Seed Purchases ---
        crop_tiles = [pos for pos in unlocked_tiles if pos not in target_pastures]
        active_strawberries = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "STRAWBERRY")
        active_melons = sum(1 for (x, y) in crop_tiles if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("crop") == "MELON")
        held_straw_seeds = seeds.get("STRAWBERRY", 0)
        held_melon_seeds = seeds.get("MELON", 0)

        safety_margin = 150 + (1000 if len(unlocked_quads) == 1 and day >= 6 else 0)
        spendable_money = max(0, money - safety_margin)

        # Strawberries (boosted if shops demand them)
        base_straw_cap = self.p["straw_target"] if num_tiles >= 75 else (20 if num_tiles >= 50 else 4)
        straw_boost = self.p["shop_straw_boost"] if (shop_demand.get("STRAWBERRY", 0) > 0) else 0
        straw_target_cap = base_straw_cap + straw_boost

        if self.p["strawberry_start_day"] <= day <= 16 and (active_strawberries + held_straw_seeds) < straw_target_cap and spendable_money >= 100:
            s_buy = min(straw_target_cap - (active_strawberries + held_straw_seeds), 4, int(spendable_money // 100))
            if s_buy > 0 and len(market_orders) < 10:
                market_orders.append(["BUY_SEED", "STRAWBERRY", s_buy])
                spendable_money -= s_buy * 100

        # Melons (boosted if shops demand them)
        base_melon_cap = self.p["melon_target"] if num_tiles >= 75 else 10
        melon_boost = self.p["shop_melon_boost"] if (shop_demand.get("MELON", 0) > 0) else 0
        melon_target_cap = base_melon_cap + melon_boost

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

        # --- Priority 6: Dynamic Market Selling (1 clean order per product) ---
        total_shed_items = sum(shed.values())
        is_emergency_dump = (total_shed_items >= self.p["emergency_shed_cap"]) or (day >= self.p["endgame_liquidation_day"]) or (money < 150 and day < 14)

        for item, count in shed.items():
            if count <= 0 or item not in PRODUCTS:
                continue
            if item in ["COW", "SHEEP", "GOOSE"]:
                continue

            cur_p = prices.get(item, 1)
            base_p = 100 if item == "FERTILIZER" else (160 if item == "MILK" else (200 if item == "WOOL" else CROPS.get(item, {}).get("base_price", 50)))
            
            thresh = 0.40 if (item == "FERTILIZER" or day < 8) else (self.p["milk_wool_thresh"] if item in ["MILK", "WOOL"] else self.p["sell_thresh"])
            
            if shop_demand.get(item, 0) > 0:
                thresh *= self.p["shop_demand_thresh_mult"]

            is_shop_tick = (step % 4 == 0) and (shop_demand.get(item, 0) > 0)
            target_batch = (self.p["sell_batch_size"] + self.p["shop_batch_bonus"]) if is_shop_tick else self.p["sell_batch_size"]

            if is_emergency_dump or cur_p >= (base_p * thresh):
                sell_qty = count if (is_emergency_dump or item == "FERTILIZER" or day >= 28) else min(count, target_batch)
                if sell_qty > 0 and len(market_orders) < 10:
                    market_orders.append(["SELL", item, sell_qty])

        # --- Spatial Multi-Worker Fleet ---
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

        # 1. Pasture building & clearing
        if (cx, cy) in target_pastures:
            if isinstance(current_tile, dict) and current_tile.get("kind") == "WEED": return ["DIG"]
            if current_tile is None: return ["BUILD_PASTURE"]

        # 2. Animal placement from inventory to pasture
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

        # 3. Shed item deposit / pickup
        if is_shed_adj:
            for it in ["MILK", "WOOL", "STRAWBERRY", "MELON", "CARROT", "TOMATO"]:
                if inv.get(it, 0) > 0: return ["PLACE", it, inv[it]]
            if inv.get("WHEAT", 0) > 4: return ["PLACE", "WHEAT", inv["WHEAT"] - 2]
            
            for a_type in ["COW", "SHEEP"]:
                if shed.get(a_type, 0) > 0 and inv.get(a_type, 0) == 0: return ["PICKUP", a_type, 1]
            
            if inv.get("WHEAT", 0) < 3 and shed.get("WHEAT", 0) > 0 and hour <= 12:
                qty = min(3 - inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                if qty > 0: return ["PICKUP", "WHEAT", qty]
            
            if day >= self.p["fert_start_day"] and inv.get("FERTILIZER", 0) < 2 and shed.get("FERTILIZER", 0) > 0 and hour <= 12:
                qty = min(2 - inv.get("FERTILIZER", 0), shed.get("FERTILIZER", 0))
                if qty > 0: return ["PICKUP", "FERTILIZER", qty]

        # 4. Animal routine on current tile
        if isinstance(current_tile, dict) and "animal" in current_tile:
            if not current_tile["fed_today"] and inv.get("WHEAT", 0) > 0: return ["FEED"]
            if not current_tile["cared_today"]: return ["CARE"]
            if current_tile.get("fertilizer_available", False): return ["COLLECT_FERTILIZER"]
            if current_tile.get("yield_units", 0) > 0: return ["HARVEST"]

        # 5. Morning animal sweep
        animal_workers = list(range(self.p["animal_keepers"]))
        if hour <= 12 and worker_idx in animal_workers:
            for (px, py) in target_pastures:
                if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                    t = farm["tiles"][py][px]
                    if isinstance(t, dict) and "animal" in t:
                        if (not t["fed_today"] and inv.get("WHEAT", 0) > 0) or (not t["cared_today"]) or t.get("fertilizer_available", False) or t.get("yield_units", 0) > 0:
                            step = get_step_towards((cx, cy), (px, py))
                            if step: return [step]

        # 6. Crop management on current tile
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
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]): should_harvest = True
                    
                    if should_harvest: return ["HARVEST"]
                    
                    if day >= self.p["fert_start_day"] and inv.get("FERTILIZER", 0) > 0 and crop in ["STRAWBERRY", "MELON"]:
                        if current_tile.get("fertilized_until_day", 0) <= day: return ["FERTILIZE"]
                    
                    if not current_tile.get("watered_today", False): return ["WATER"]
            
            elif current_tile is None and day < 27:
                seeds = private.get("seeds", {})
                for c in ["STRAWBERRY", "MELON", "WHEAT", "CARROT", "TOMATO"]:
                    if seeds.get(c, 0) > 0: return ["PLANT", c]

        # 7. Deposit produce to shed
        has_produce = any(inv.get(it, 0) > 0 for it in ["MILK", "WOOL", "STRAWBERRY", "MELON", "CARROT", "TOMATO"])
        if has_produce and (hour >= 17 or sum(inv.values()) >= 5):
            closest_shed = min(SHED_ACCESS, key=lambda s_pos: abs(cx - s_pos[0]) + abs(cy - s_pos[1]))
            step = get_step_towards((cx, cy), closest_shed)
            if step: return [step]

        # 8. Target urgent assigned crop/weed tile
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
                        if age >= cd["max_yield_day"] or (day >= 28 and age >= cd["first_yield_day"]): should_harvest = True
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

        # 9. Pasture building target
        for (px, py) in target_pastures:
            if px < len(farm["tiles"][0]) and py < len(farm["tiles"]):
                if farm["tiles"][py][px] is None:
                    step = get_step_towards((cx, cy), (px, py))
                    if step: return [step]

        # 10. Return to home tile
        if assigned_tiles:
            home = assigned_tiles[0]
            if (cx, cy) != home:
                step = get_step_towards((cx, cy), home)
                if step: return [step]

        return ["PASS"]


# --- TOP-LEVEL OBJECTIVE FOR MULTI-CORE OPTUNA ---
def evaluate_params(params):
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)

    def agent_wrapper(obs):
        if obs.get("step", 0) == 0:
            agent_wrapper.instance = AdaptiveApexAgent(params)
        return agent_wrapper.instance.act(obs)

    scores = []
    # 2 games: 1 as P0, 1 as P1 for balanced evaluation
    for game_idx in range(2):
        as_p0 = (game_idx % 2 == 0)
        agents = [agent_wrapper, "starter"] if as_p0 else ["starter", agent_wrapper]
        env.run(agents)
        p_idx = 0 if as_p0 else 1
        reward = env.steps[-1][p_idx]["reward"] or 0
        scores.append(reward)

    return sum(scores) / len(scores)


def objective(trial):
    params = {
        "sell_thresh": trial.suggest_categorical("sell_thresh", [0.60, 0.65, 0.70, 0.75]),
        "milk_wool_thresh": trial.suggest_categorical("milk_wool_thresh", [0.50, 0.55, 0.60, 0.65]),
        "sell_batch_size": trial.suggest_categorical("sell_batch_size", [5, 6, 8, 10]),
        "shop_demand_thresh_mult": trial.suggest_categorical("shop_demand_thresh_mult", [0.80, 0.85, 0.90, 0.95]),
        "shop_batch_bonus": trial.suggest_categorical("shop_batch_bonus", [2, 4, 6]),
        
        "straw_target": trial.suggest_categorical("straw_target", [20, 25, 30, 35]),
        "melon_target": trial.suggest_categorical("melon_target", [12, 15, 18, 20]),
        "melon_cutoff_day": trial.suggest_categorical("melon_cutoff_day", [16, 17, 18, 19]),
        "shop_straw_boost": trial.suggest_categorical("shop_straw_boost", [0, 5, 10]),
        "shop_melon_boost": trial.suggest_categorical("shop_melon_boost", [0, 3, 6]),
        "strawberry_start_day": trial.suggest_categorical("strawberry_start_day", [6, 8, 10]),
        "fert_start_day": trial.suggest_categorical("fert_start_day", [4, 6, 8]),

        "max_animals_quad2": trial.suggest_categorical("max_animals_quad2", [10, 12, 14]),
        "animal_cutoff_day": trial.suggest_categorical("animal_cutoff_day", [12, 14, 16]),
        "animal_min_cash": trial.suggest_categorical("animal_min_cash", [500, 600, 750, 900]),
        "feed_buffer_per_animal": trial.suggest_categorical("feed_buffer_per_animal", [2, 3]),

        "tiles_per_worker": trial.suggest_categorical("tiles_per_worker", [4.5, 5.0, 5.5]),
        "animal_keepers": trial.suggest_categorical("animal_keepers", [2, 3]),
        "hire_cutoff_hour": trial.suggest_categorical("hire_cutoff_hour", [4, 6]),
        "late_worker_surge": trial.suggest_categorical("late_worker_surge", [0, 2, 4]),

        "quad2_day_cutoff": trial.suggest_categorical("quad2_day_cutoff", [7, 8, 9]),
        "quad3_day_cutoff": trial.suggest_categorical("quad3_day_cutoff", [11, 12, 13]),
        "quad4_enable": trial.suggest_categorical("quad4_enable", [False, True]),
        "emergency_shed_cap": trial.suggest_categorical("emergency_shed_cap", [65, 70, 75]),
        "endgame_liquidation_day": trial.suggest_categorical("endgame_liquidation_day", [27, 28])
    }
    return evaluate_params(params)


def run_optimization(n_trials=60, n_jobs=1):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    storage_name = "sqlite:///optuna_study.db"
    study = optuna.create_study(study_name="apex_tuning", storage=storage_name, load_if_exists=True, direction="maximize")
    
    print(f"Starting Optimization ({n_trials} trials, jobs={n_jobs})...\n")
    
    import json

    with tqdm(total=n_trials, desc="Tuning Adaptive Apex V3", unit="trial") as pbar:
        def callback(study, trial):
            try:
                pbar.set_postfix({
                    "Best Score": f"${study.best_value:,.2f}",
                    "Trial Score": f"${trial.value:,.2f}" if trial.value is not None else "N/A"
                })
                pbar.update(1)
                
                # Real-time export whenever a new high score is achieved
                if trial.value is not None and trial.value >= study.best_value:
                    with open("best_params.json", "w") as f:
                        json.dump(study.best_params, f, indent=2)
            except Exception:
                pass

        try:
            study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, callbacks=[callback])
        except KeyboardInterrupt:
            print("\nOptimization paused by user.")
        except Exception as e:
            print(f"\nNotice: {e}")

    try:
        print("\n" + "=" * 50)
        print(f"Optimization Complete! Best Score: ${study.best_value:,.2f}")
        print("=" * 50)
        print("Best Parameters Found:")
        for key, value in study.best_params.items():
            print(f'  "{key}": {value},')

        with open("best_params.json", "w") as f:
            json.dump(study.best_params, f, indent=2)
        print("\nSaved best parameters to best_params.json")
    except Exception:
        pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_optimization(n_trials=120, n_jobs=1)