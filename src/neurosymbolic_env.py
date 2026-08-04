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

        # Observation Space: A condensed 1D vector representing global economic state
        # [Day, Hour, My Cash, Opp Cash, My Cows, My Sheep, Melon Price, Straw Price, Milk Price, Wool Price]
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(10,), dtype=np.float32)

        self.current_state = None
        self.trainer = None

        # Load the Symbolic Engine (Our rule-based baseline)
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from Archive.baseline import ApexGrandmasterAgent
        self.symbolic_engine = ApexGrandmasterAgent()

    def reset(self):
        # Initialize Kaggle environment with the "Final Boss" opponent
        self.trainer = self.kaggle_env.train([None, self.opponent])
        raw_obs = self.trainer.reset()
        self.current_state = raw_obs
        return self._extract_features(raw_obs)

    def _extract_features(self, raw_obs):
        """
        Translates the massive grid dictionary into a neat 1D vector for the Neural Net.
        """
        player_id = raw_obs.get("player", 0)
        farms = raw_obs.get("farms", [])

        if len(farms) < 2:
             return np.zeros(10, dtype=np.float32)

        my_farm = farms[player_id]
        opp_farm = farms[1 - player_id]

        day = raw_obs.get("day", 0)
        hour = raw_obs.get("hour", 0)
        my_cash = my_farm.get("money", 0)
        opp_cash = opp_farm.get("money", 0)

        # Count animals
        my_cows, my_sheep = self._count_animals(my_farm)

        prices = raw_obs.get("market", {}).get("prices", {})
        melon_p = prices.get("MELON", 250)
        straw_p = prices.get("STRAWBERRY", 120)
        milk_p = prices.get("MILK", 160)
        wool_p = prices.get("WOOL", 200)

        features = np.array([
            day, hour, my_cash, opp_cash, my_cows, my_sheep,
            melon_p, straw_p, milk_p, wool_p
        ], dtype=np.float32)

        return features

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
        3. Ask the Symbolic Engine to generate actual grid commands.
        4. Step the Kaggle environment.
        5. Return new state and reward.
        """

        # --- NEUROSYMBOLIC BRIDGE ---
        # The Neural Net dictates the strategy by modifying the Symbolic Engine's strict rules
        if action == 1: # FOCUS_MELON
            self.symbolic_engine.p["melon_cutoff_day"] = 30 # Never stop planting melons
            self.symbolic_engine.p["strawberry_start_day"] = 30 # Disable strawberries
        elif action == 2: # FOCUS_STRAWBERRY
            self.symbolic_engine.p["strawberry_start_day"] = 0 # Plant strawberries immediately
            self.symbolic_engine.p["melon_cutoff_day"] = 0 # Disable melons
        elif action == 3: # BUY_COW
            self.symbolic_engine.p["max_cows"] = 20 # Force engine to prioritize cows
        elif action == 4: # BUY_SHEEP
            self.symbolic_engine.p["max_sheep"] = 20 # Force engine to prioritize sheep
        elif action == 5: # BUY_LAND
            self.symbolic_engine.p["quad2_day_cutoff"] = 30 # Allow expansion anytime
        elif action == 6: # PANIC_SELL
            self.symbolic_engine.p["sell_thresh"] = 0.0 # Force sell everything
            self.symbolic_engine.p["milk_wool_thresh"] = 0.0

        # Let the Symbolic Engine do the hard work of routing workers
        symbolic_action = self.symbolic_engine.act(self.current_state)

        # Step the actual Kaggle environment
        raw_obs, raw_reward, done, info = self.trainer.step(symbolic_action)
        self.current_state = raw_obs

        # Reset the engine parameters to defaults for the next step so actions are discrete choices
        self.symbolic_engine.p["melon_cutoff_day"] = 10
        self.symbolic_engine.p["strawberry_start_day"] = 10
        self.symbolic_engine.p["max_cows"] = 8
        self.symbolic_engine.p["max_sheep"] = 5
        self.symbolic_engine.p["sell_thresh"] = 0.65
        self.symbolic_engine.p["milk_wool_thresh"] = 0.55

        # Neurosymbolic Reward:
        # For Kaggriculture, we want to maximize our cash differential over the opponent.
        # So reward is roughly delta(My Cash - Opp Cash)
        features = self._extract_features(raw_obs)
        reward = features[2] - features[3] # My Cash - Opp Cash

        return features, reward, done, info
