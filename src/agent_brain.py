from src.constants import CROPS, PRODUCTS, MAX_MARKET_ORDERS_PER_TURN, TOTAL_DAYS
from src.economy import select_best_crop_portfolio, should_buy_land
from src.worker_manager import WorkerManager


class AgricultureAgent:
    def __init__(self):
        self.worker_manager = WorkerManager()
        self.last_day = -1
        self.planned_plants_today = []

    def act(self, obs):
        player_id = obs["player"]
        farm = obs["farms"][player_id]
        private = obs["private"]
        market_info = obs.get("market", {})
        prices = market_info.get("prices", {})
        inventory = market_info.get("inventory", {})
        day = obs.get("day", 0)
        hour = obs.get("hour", 0)
        money = farm["money"]
        board_size = len(farm["tiles"])
        
        market_orders = []

        # --- Hour 0: Daily Strategic Planning & Market Purchasing ---
        if hour == 0 or self.last_day != day:
            self.last_day = day
            
            # 1. Count empty unlocked tiles and active crops
            empty_tiles = []
            active_crops = {}
            for y in range(board_size):
                for x in range(board_size):
                    t = farm["tiles"][y][x]
                    if t is None:
                        empty_tiles.append((x, y))
                    elif isinstance(t, dict) and t.get("kind") == "PLANT":
                        c = t["crop"]
                        active_crops[c] = active_crops.get(c, 0) + 1

            # 2. Check Land Expansion
            unlocked_count = len(farm["unlocked_quadrants"])
            active_tile_count = board_size * board_size - len(empty_tiles)
            if should_buy_land(money, unlocked_count, day, active_tile_count):
                market_orders.append(["BUY_LAND"])

            # 3. Select Seed Portfolio
            # Available money after potential land purchase & reserve
            avail_money = money - (1000 if "BUY_LAND" in [o[0] for o in market_orders] else 0)
            avail_money = max(0, avail_money - 20)  # buffer for hiring
            
            portfolio = select_best_crop_portfolio(
                current_day=day,
                empty_tile_count=len(empty_tiles),
                money=avail_money,
                market_prices=prices,
                market_inventory=inventory,
                active_crops=active_crops
            )

            # Assign specific tiles to planned seeds
            self.planned_plants_today = []
            tile_idx = 0
            for crop, count in portfolio.items():
                if count > 0:
                    market_orders.append(["BUY_SEED", crop, count])
                    for _ in range(count):
                        if tile_idx < len(empty_tiles):
                            tx, ty = empty_tiles[tile_idx]
                            self.planned_plants_today.append((tx, ty, crop))
                            tile_idx += 1

            # 4. Plan Worker Schedule
            self.worker_manager.start_new_day(obs, player_id, self.planned_plants_today)

            # 5. Queue Worker Hires for Hour 0
            for _ in range(self.worker_manager.planned_hires_today):
                if len(market_orders) < MAX_MARKET_ORDERS_PER_TURN:
                    market_orders.append(["HIRE"])

        # --- Continuous Market Actions: Selling Stored Produce ---
        shed = private.get("shed", {})
        for item, count in shed.items():
            if count > 0 and item in PRODUCTS:
                # Sell batch
                if len(market_orders) < MAX_MARKET_ORDERS_PER_TURN:
                    market_orders.append(["SELL", item, count])

        # Limit to max allowed orders per turn
        market_orders = market_orders[:MAX_MARKET_ORDERS_PER_TURN]

        # --- Unit Action Execution ---
        farmer_act, hands_acts = self.worker_manager.get_actions_for_turn(hour)

        # Slice hands_acts to match actual number of hands currently spawned
        actual_hands_count = len(farm.get("hands", []))
        if len(hands_acts) > actual_hands_count:
            hands_acts = hands_acts[:actual_hands_count]
        elif len(hands_acts) < actual_hands_count:
            hands_acts.extend([["PASS"]] * (actual_hands_count - len(hands_acts)))

        return {
            "farmer": farmer_act,
            "hands": hands_acts,
            "market": market_orders,
        }
