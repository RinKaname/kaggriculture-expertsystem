"""Evaluation & Tournament Benchmark for the Trained Multi-Expert Neurosymbolic Agent."""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import torch
from stable_baselines3 import PPO
from kaggle_environments import make
from Archive.baseline import ApexGrandmasterAgent
from src.multi_expert_engine import MultiExpertSystem
from train_hybrid_cnn import HybridCNNFeaturesExtractor
import main


class TrainedNeurosymbolicAgent:
    def __init__(self, model_path="neurosymbolic_cfo_weights.zip"):
        self.model = PPO.load(model_path)
        self.expert_engine = MultiExpertSystem()
        self.last_day = -1
        self.current_macro_action = 0

    def reset(self):
        self.expert_engine.reset()
        self.last_day = -1
        self.current_macro_action = 0

    def _extract_spatial_features(self, farm, current_day):
        grid = np.zeros((5, 10, 10), dtype=np.float32)
        tiles = farm.get("tiles", [])
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if y >= 10 or x >= 10:
                    continue
                if tile != "LOCKED":
                    grid[0, y, x] = 1.0
                    if isinstance(tile, dict):
                        kind = tile.get("kind")
                        if kind == "WEED":
                            grid[1, y, x] = 1.0
                        elif kind == "PLANT":
                            planted_day = tile.get("planted_day", current_day)
                            age = max(0, current_day - planted_day)
                            grid[2, y, x] = min(1.0, age / 10.0)
                        animal = tile.get("animal")
                        if animal == "COW":
                            grid[3, y, x] = 1.0
                        elif animal == "SHEEP":
                            grid[3, y, x] = 0.5
                        elif animal == "GOOSE":
                            grid[3, y, x] = 0.25

        if "farmer" in farm:
            fx, fy = farm["farmer"]
            if 0 <= fx < 10 and 0 <= fy < 10:
                grid[4, fy, fx] = 1.0

        for hx, hy in farm.get("hands", []):
            if 0 <= hx < 10 and 0 <= hy < 10:
                grid[4, hy, hx] = 0.5

        return grid

    def _extract_features(self, raw_obs):
        player_id = raw_obs.get("player", 0)
        farms = raw_obs.get("farms", [])
        if len(farms) < 2:
            return {
                "economy": np.zeros(18, dtype=np.float32),
                "spatial": np.zeros((5, 10, 10), dtype=np.float32)
            }

        my_farm = farms[player_id]
        opp_farm = farms[1 - player_id]
        market = raw_obs.get("market", {})
        private = raw_obs.get("private", {})
        my_shed = private.get("shed", {})

        day = float(raw_obs.get("day", 0))
        hour = float(raw_obs.get("hour", 0))
        my_cash = float(my_farm.get("money", 0))
        opp_cash = float(opp_farm.get("money", 0))

        cows = 0
        sheep = 0
        for row in my_farm.get("tiles", []):
            for tile in row:
                if isinstance(tile, dict) and tile.get("kind") in ["COOP", "PASTURE"]:
                    animal = tile.get("animal")
                    if animal == "COW": cows += 1
                    elif animal == "SHEEP": sheep += 1

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

        economy = np.array([
            day, hour, my_cash, opp_cash, cows, sheep,
            melon_p, straw_p, milk_p, wool_p,
            my_melons_shed, my_straws_shed, my_milk_shed, my_wool_shed,
            my_quads, opp_quads, yarn_unlocked, pizza_unlocked
        ], dtype=np.float32)

        spatial = self._extract_spatial_features(my_farm, day)

        return {
            "economy": economy,
            "spatial": spatial
        }

    def __call__(self, obs_dict, configuration=None):
        day = obs_dict.get("day", 0)
        hour = obs_dict.get("hour", 0)
        step = obs_dict.get("step", 0)

        if step == 0 or day < self.last_day:
            self.reset()

        if day != self.last_day and hour == 0:
            self.last_day = day
            features = self._extract_features(obs_dict)
            action, _states = self.model.predict(features, deterministic=True)
            self.current_macro_action = int(action)

        return self.expert_engine.act(obs_dict, macro_action=self.current_macro_action)


def rule_bot(obs, configuration=None):
    if not hasattr(rule_bot, "engine") or obs.get("step", 0) == 0:
        rule_bot.engine = ApexGrandmasterAgent()
    return rule_bot.engine.act(obs)


def run_benchmark():
    print("=" * 65)
    print("[*] TOURNAMENT BENCHMARK: Multi-Expert Neurosymbolic Agent")
    print("=" * 65)

    agent = TrainedNeurosymbolicAgent()

    # Match 1: vs Starter
    print("\n--- [Match 1] Multi-Expert Agent (P0) vs Starter (P1) ---")
    env1 = make("kaggriculture", debug=False)
    env1.run([agent, "starter"])
    p0_score = env1.steps[-1][0]["reward"]
    p1_score = env1.steps[-1][1]["reward"]
    print(f"Result -> Multi-Expert: ${p0_score:,} | Starter: ${p1_score:,} | Margin: {p0_score - p1_score:+,}")

    # Match 2: vs Apex Rule Baseline
    print("\n--- [Match 2] Multi-Expert Agent (P0) vs Apex Rule Baseline (P1) ---")
    env2 = make("kaggriculture", debug=False)
    env2.run([agent, rule_bot])
    p0_score = env2.steps[-1][0]["reward"]
    p1_score = env2.steps[-1][1]["reward"]
    print(f"Result -> Multi-Expert: ${p0_score:,} | Rule Baseline: ${p1_score:,} | Margin: {p0_score - p1_score:+,}")

    # Match 3: vs Main V1
    print("\n--- [Match 3] Multi-Expert Agent (P0) vs Main V1 (P1) ---")
    env3 = make("kaggriculture", debug=False)
    env3.run([agent, main.agent])
    p0_score = env3.steps[-1][0]["reward"]
    p1_score = env3.steps[-1][1]["reward"]
    print(f"Result -> Multi-Expert: ${p0_score:,} | Main V1: ${p1_score:,} | Margin: {p0_score - p1_score:+,}")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmark()
