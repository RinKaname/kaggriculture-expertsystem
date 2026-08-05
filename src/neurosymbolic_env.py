import gymnasium as gym
from gymnasium import spaces
import numpy as np
from kaggle_environments import make

# --- HIGH LEVEL MACRO ACTIONS ---
# 0: DO_NOTHING (Maintain current operations)
# 1: FOCUS_MELON (Spend excess cash on Melon seeds)
# 2: FOCUS_STRAWBERRY (Spend excess cash on Strawberry seeds)
# 3: BUY_COW (Attempt to buy a cow if cash/pastures allow)
# 4: BUY_SHEEP (Attempt to buy a sheep if cash/pastures allow)
# 5: BUY_LAND (Attempt to expand farm)
# 6: PANIC_SELL (Liquidate all inventory currently in shed)
NUM_MACRO_ACTIONS = 7

class KaggricultureNeurosymbolicEnv(gym.Env):
    """
    A Gym environment wrapper that turns the raw Kaggle grid into a macro-management game.
    The RL agent chooses high-level strategies, and the underlying Symbolic Engine (rules)
    translates those into precise worker movements and grid actions.
    """

    def __init__(self, opponent="main.py"):
        super(KaggricultureNeurosymbolicEnv, self).__init__()

        self.kaggle_env = make("kaggriculture", debug=False)
        self.opponent = opponent

        # Action Space: Discrete high-level strategic choices
        self.action_space = spaces.Discrete(NUM_MACRO_ACTIONS)

        # Hybrid Observation Space:
        # 'economy': 18D Box for global market and cash features
        # 'spatial': 10x10x5 Box representing the farm grid (Channels: 0: Locked/Unlocked, 1: Weed Age, 2: Crop Age, 3: Animal Presence, 4: Worker Presence)
        self.observation_space = spaces.Dict({
            "economy": spaces.Box(low=0, high=np.inf, shape=(18,), dtype=np.float32),
            "spatial": spaces.Box(low=0, high=np.inf, shape=(5, 10, 10), dtype=np.float32)
        })

        self.current_state = None
        self.trainer = None

        # Load the Symbolic Engine (Our rule-based baseline)
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from Archive.baseline import ApexGrandmasterAgent
        self.symbolic_engine = ApexGrandmasterAgent()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        from Archive.baseline import ApexGrandmasterAgent
        self.symbolic_engine = ApexGrandmasterAgent()
        # Initialize Kaggle environment with the "Final Boss" opponent
        self.trainer = self.kaggle_env.train([None, self.opponent])
        raw_obs = self.trainer.reset()
        self.current_state = raw_obs
        return self._extract_features(raw_obs), {}

    def _extract_features(self, raw_obs):
        """
        Translates the massive grid dictionary into a neat 1D vector for the Neural Net.
        """
        player_id = raw_obs.get("player", 0)
        farms = raw_obs.get("farms", [])

        if len(farms) < 2:
            return {
                "economy": np.zeros(18, dtype=np.float32),
                "spatial": np.zeros((5, 10, 10), dtype=np.float32)
            }

        my_farm = farms[player_id]
        opp_farm = farms[1 - player_id]
        private = raw_obs.get("private", {})
        my_shed = private.get("shed", {})
        market = raw_obs.get("market", {})

        day = raw_obs.get("day", 0)
        hour = raw_obs.get("hour", 0)
        my_cash = my_farm.get("money", 0)
        opp_cash = opp_farm.get("money", 0)

        # Count animals
        my_cows, my_sheep = self._count_animals(my_farm)

        # Market Prices
        prices = market.get("prices", {})
        melon_p = prices.get("MELON", 250)
        straw_p = prices.get("STRAWBERRY", 120)
        milk_p = prices.get("MILK", 160)
        wool_p = prices.get("WOOL", 200)

        # My Shed Inventory
        my_melons_shed = my_shed.get("MELON", 0)
        my_straws_shed = my_shed.get("STRAWBERRY", 0)
        my_milk_shed = my_shed.get("MILK", 0)
        my_wool_shed = my_shed.get("WOOL", 0)

        # Land Expansion
        my_quads = len(my_farm.get("unlocked_quadrants", []))
        opp_quads = len(opp_farm.get("unlocked_quadrants", []))

        # Town Shops Status
        town = market.get("town", {})
        yarn_unlocked = 1 if "YARN_STORE" in town else 0
        pizza_unlocked = 1 if "PIZZA_SHOP" in town else 0

        features = np.array([
            day, hour, my_cash, opp_cash, my_cows, my_sheep,
            melon_p, straw_p, milk_p, wool_p,
            my_melons_shed, my_straws_shed, my_milk_shed, my_wool_shed,
            my_quads, opp_quads, yarn_unlocked, pizza_unlocked
        ], dtype=np.float32)

        spatial_features = self._extract_spatial_features(my_farm, day)

        return {
            "economy": features,
            "spatial": spatial_features
        }

    def _extract_spatial_features(self, farm, current_day):
        """
        Extracts a (5, 10, 10) channels-first tensor representing the spatial layout of the farm.
        Channel 0: Unlocked (1) or Locked (0)
        Channel 1: Weed Age (0 if no weed)
        Channel 2: Crop Age (0 if no crop)
        Channel 3: Animal (1 if cow, 2 if sheep, 3 if goose, etc. 0 otherwise)
        Channel 4: Worker Presence (1 if worker is here, 0 otherwise)
        """
        grid = np.zeros((5, 10, 10), dtype=np.float32)

        # Populate Channels 0-3 based on tiles
        tiles = farm.get("tiles", [])
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if y >= 10 or x >= 10: continue # Safeguard bounds

                if tile != "LOCKED":
                    grid[0, y, x] = 1.0 # Unlocked

                    if isinstance(tile, dict):
                        kind = tile.get("kind")
                        if kind == "WEED":
                            grid[1, y, x] = float(current_day - tile.get("planted_day", current_day))
                        elif kind == "PLANT":
                            grid[2, y, x] = float(current_day - tile.get("planted_day", current_day))

                        animal = tile.get("animal")
                        if animal == "COW":
                            grid[3, y, x] = 1.0
                        elif animal == "SHEEP":
                            grid[3, y, x] = 2.0
                        elif animal: # generic other
                            grid[3, y, x] = 3.0

        # Populate Channel 4 for worker presence
        if "farmer" in farm:
            fx, fy = farm["farmer"]
            if 0 <= fx < 10 and 0 <= fy < 10:
                grid[4, fy, fx] = 1.0

        for hx, hy in farm.get("hands", []):
            if 0 <= hx < 10 and 0 <= hy < 10:
                grid[4, hy, hx] = 1.0

        return grid

    def _count_animals(self, farm):
        cows = 0
        sheep = 0
        for row in farm.get("tiles", []):
            for tile in row:
                if isinstance(tile, dict) and "animal" in tile:
                    if tile["animal"] == "COW": cows += 1
                    if tile["animal"] == "SHEEP": sheep += 1
        return cows, sheep

    def step(self, action):
        """
        1. Take the macro action from the Neural Net.
        2. Modulate the Symbolic Engine's parameters based on the action.
        3. Step the Kaggle environment for an entire MACRO-STEP (e.g. 24 steps / 1 full day).
        4. Return new state and reward.
        """

        # --- NEUROSYMBOLIC BRIDGE ---
        # The Neural Net dictates the strategy by modifying the Symbolic Engine's strict rules
        if action == 1: # FOCUS_MELON
            self.symbolic_engine.p["melon_cutoff_day"] = 30 # Never stop planting melons
            self.symbolic_engine.p["strawberry_start_day"] = 30 # Disable strawberries
        elif action == 2: # FOCUS_STRAWBERRY
            self.symbolic_engine.p["strawberry_start_day"] = 0 # Plant strawberries immediately
            self.symbolic_engine.p["melon_cutoff_day"] = 0 # Disable melons
            self.symbolic_engine.p["straw_target"] = 6
        elif action == 3: # BUY_COW
            self.symbolic_engine.p["max_cows"] = 8 # Force engine to prioritize cows
        elif action == 4: # BUY_SHEEP
            self.symbolic_engine.p["max_sheep"] = 5 # Force engine to prioritize sheep
        elif action == 5: # BUY_LAND
            self.symbolic_engine.p["quad2_day_cutoff"] = 30 # Allow expansion anytime
        elif action == 6: # PANIC_SELL
            self.symbolic_engine.p["sell_thresh"] = 0.0 # Force sell everything
            self.symbolic_engine.p["milk_wool_thresh"] = 0.0

        MACRO_STEP_SIZE = 24

        for _ in range(MACRO_STEP_SIZE):
            # Let the Symbolic Engine do the hard work of routing workers
            symbolic_action = self.symbolic_engine.act(self.current_state)

            # Step the actual Kaggle environment
            raw_obs, raw_reward, done, info = self.trainer.step(symbolic_action)
            self.current_state = raw_obs

            if done:
                break

        # Reset the engine parameters to defaults for the next macro-step
        self.symbolic_engine.p["melon_cutoff_day"] = 10
        self.symbolic_engine.p["strawberry_start_day"] = 10
        self.symbolic_engine.p["straw_target"] = 6
        self.symbolic_engine.p["max_cows"] = 8
        self.symbolic_engine.p["max_sheep"] = 5
        self.symbolic_engine.p["sell_thresh"] = 0.65
        self.symbolic_engine.p["milk_wool_thresh"] = 0.55

        # Neurosymbolic Reward:
        # For Kaggriculture, we want to maximize our cash differential over the opponent.
        # We calculate the reward at the END of the macro-step.
        features = self._extract_features(self.current_state)
        # Scaled reward to keep policy gradients well-conditioned (in units of $1,000)
        reward = float((features["economy"][2] - features["economy"][3]) / 1000.0)

        # We set truncated to False to match the gymnasium API
        truncated = False

        return features, reward, done, truncated, info
