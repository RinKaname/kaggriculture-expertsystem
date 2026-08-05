"""Evaluation & Tournament Benchmark for the Trained Neurosymbolic CFO Agent."""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from stable_baselines3 import PPO
from kaggle_environments import make
from Archive.baseline import ApexGrandmasterAgent
import main

class TrainedNeurosymbolicAgent:
    def __init__(self, model_path="neurosymbolic_cfo_weights.zip"):
        self.model = PPO.load(model_path)
        self.symbolic_engine = ApexGrandmasterAgent()
        self.last_day = -1

    def reset(self):
        self.symbolic_engine = ApexGrandmasterAgent()
        self.last_day = -1

    def _extract_features(self, raw_obs):
        player_id = raw_obs.get("player", 0)
        farms = raw_obs.get("farms", [])
        if len(farms) < 2:
            return np.zeros(18, dtype=np.float32)

        my_farm = farms[player_id]
        opp_farm = farms[1 - player_id]
        private = raw_obs.get("private", {})
        my_shed = private.get("shed", {})
        market = raw_obs.get("market", {})

        day = raw_obs.get("day", 0)
        hour = raw_obs.get("hour", 0)
        my_cash = my_farm.get("money", 0)
        opp_cash = opp_farm.get("money", 0)

        # Animals
        cows, sheep = 0, 0
        for row in my_farm.get("tiles", []):
            for tile in row:
                if isinstance(tile, dict) and "animal" in tile:
                    if tile["animal"] == "COW": cows += 1
                    if tile["animal"] == "SHEEP": sheep += 1

        prices = market.get("prices", {})
        melon_p = prices.get("MELON", 250)
        straw_p = prices.get("STRAWBERRY", 120)
        milk_p = prices.get("MILK", 160)
        wool_p = prices.get("WOOL", 200)

        my_melons_shed = my_shed.get("MELON", 0)
        my_straws_shed = my_shed.get("STRAWBERRY", 0)
        my_milk_shed = my_shed.get("MILK", 0)
        my_wool_shed = my_shed.get("WOOL", 0)

        my_quads = len(my_farm.get("unlocked_quadrants", []))
        opp_quads = len(opp_farm.get("unlocked_quadrants", []))

        town = market.get("town", {})
        yarn_unlocked = 1 if "YARN_STORE" in town else 0
        pizza_unlocked = 1 if "PIZZA_SHOP" in town else 0

        return np.array([
            day, hour, my_cash, opp_cash, cows, sheep,
            melon_p, straw_p, milk_p, wool_p,
            my_melons_shed, my_straws_shed, my_milk_shed, my_wool_shed,
            my_quads, opp_quads, yarn_unlocked, pizza_unlocked
        ], dtype=np.float32)

    def __call__(self, obs, configuration=None):
        # Handle dict or Struct obs
        obs_dict = dict(obs) if not isinstance(obs, dict) else obs
        day = obs_dict.get("day", 0)
        hour = obs_dict.get("hour", 0)
        step = obs_dict.get("step", 0)

        if step == 0 or day < self.last_day:
            self.reset()

        if day != self.last_day and hour == 0:
            self.last_day = day
            features = self._extract_features(obs_dict)
            action, _states = self.model.predict(features, deterministic=True)
            macro_action = int(action)

            # Modulate Symbolic Engine rules
            if macro_action == 1: # FOCUS_MELON
                self.symbolic_engine.p["melon_cutoff_day"] = 30
                self.symbolic_engine.p["strawberry_start_day"] = 30
            elif macro_action == 2: # FOCUS_STRAWBERRY
                self.symbolic_engine.p["strawberry_start_day"] = 0
                self.symbolic_engine.p["melon_cutoff_day"] = 0
            elif macro_action == 3: # BUY_COW
                self.symbolic_engine.p["max_cows"] = 8
            elif macro_action == 4: # BUY_SHEEP
                self.symbolic_engine.p["max_sheep"] = 5
            elif macro_action == 5: # BUY_LAND
                self.symbolic_engine.p["quad2_day_cutoff"] = 30
            elif macro_action == 6: # PANIC_SELL
                self.symbolic_engine.p["sell_thresh"] = 0.0
                self.symbolic_engine.p["milk_wool_thresh"] = 0.0

        return self.symbolic_engine.act(obs_dict)


def rule_bot(obs, configuration=None):
    if not hasattr(rule_bot, "engine") or obs.get("step", 0) == 0:
        rule_bot.engine = ApexGrandmasterAgent()
    return rule_bot.engine.act(obs)

def run_benchmark():
    print("=" * 65)
    print("[*] TOURNAMENT BENCHMARK: Trained Neurosymbolic Agent")
    print("=" * 65)

    neuro_agent = TrainedNeurosymbolicAgent("neurosymbolic_cfo_weights.zip")

    # Match 1: vs Starter
    print("\n--- [Match 1] Neurosymbolic (P0) vs Starter (P1) ---")
    neuro_agent.reset()
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.run([neuro_agent, "starter"])
    r0 = env.steps[-1][0].reward or 0
    r1 = env.steps[-1][1].reward or 0
    print(f"Result -> Neurosymbolic: ${r0:,.0f} | Starter: ${r1:,.0f} | Margin: {r0 - r1:+,.0f}")

    # Match 2: vs Rule-based Baseline
    print("\n--- [Match 2] Neurosymbolic (P0) vs Apex Rule Baseline (P1) ---")
    neuro_agent.reset()
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.run([neuro_agent, rule_bot])
    r0 = env.steps[-1][0].reward or 0
    r1 = env.steps[-1][1].reward or 0
    print(f"Result -> Neurosymbolic: ${r0:,.0f} | Rule Baseline: ${r1:,.0f} | Margin: {r0 - r1:+,.0f}")

    # Match 3: vs Main V1 Grandmaster
    print("\n--- [Match 3] Neurosymbolic (P0) vs Main V1 (P1) ---")
    neuro_agent.reset()
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.run([neuro_agent, main.agent])
    r0 = env.steps[-1][0].reward or 0
    r1 = env.steps[-1][1].reward or 0
    print(f"Result -> Neurosymbolic: ${r0:,.0f} | Main V1: ${r1:,.0f} | Margin: {r0 - r1:+,.0f}")
    print("=" * 65)

if __name__ == "__main__":
    run_benchmark()
