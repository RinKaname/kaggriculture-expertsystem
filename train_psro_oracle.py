"""PSRO (Policy Space Response Oracles) Best-Response RL Training Pipeline.
Trains the Hybrid CNN + MLP PPO Strategist against a dynamic population mixture
of Grandmaster opponents (VN-Orion 182k Tape, Subin An Moon V14, Apex Baseline).
"""
import os
import random
import numpy as np
import torch
import torch.nn as nn
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.callbacks import BaseCallback
from kaggle_environments import make

from src.multi_expert_engine import MultiExpertSystem
from src.subin_an_tape import agent as subin_agent
from Archive.baseline import agent as baseline_agent


# ---------------------------------------------------------------------------
# 1. HYBRID CNN + MLP FEATURE EXTRACTOR (232,648 PARAMETERS)
# ---------------------------------------------------------------------------
class HybridCNNFeaturesExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space: spaces.Dict, features_dim: int = 128):
        super(HybridCNNFeaturesExtractor, self).__init__(observation_space, features_dim)
        
        # Spatial Grid Branch: 5 channels x 10 x 10 grid
        self.cnn = nn.Sequential(
            nn.Conv2d(5, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(32 * 10 * 10, 64),
            nn.ReLU()
        )
        
        # Economic Vector Branch: 18 market / cash features
        self.mlp = nn.Sequential(
            nn.Linear(18, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU()
        )
        
        self._features_dim = 128

    def forward(self, observations):
        spatial_feat = self.cnn(observations["spatial"])
        econ_feat = self.mlp(observations["economy"])
        return torch.cat([spatial_feat, econ_feat], dim=1)


# ---------------------------------------------------------------------------
# 2. DYNAMIC PSRO POPULATION ENVIRONMENT
# ---------------------------------------------------------------------------
class PSROPopulationEnv(gym.Env):
    """
    Gymnasium environment that dynamically pits the learning agent against
    the PSRO Meta-Nash opponent mixture across episodes.
    """
    def __init__(self, opponent_pool=None):
        super(PSROPopulationEnv, self).__init__()
        
        if opponent_pool is None:
            self.opponent_pool = [
                ("Moon V14", subin_agent, 0.45),
                ("Main V1 Tape", "main.py", 0.40),
                ("Apex Baseline", baseline_agent, 0.15),
            ]
        else:
            self.opponent_pool = opponent_pool

        self.action_space = spaces.Discrete(7)
        self.observation_space = spaces.Dict({
            "economy": spaces.Box(low=0, high=np.inf, shape=(18,), dtype=np.float32),
            "spatial": spaces.Box(low=0, high=np.inf, shape=(5, 10, 10), dtype=np.float32)
        })

        self.expert_engine = MultiExpertSystem()
        self.current_obs = None
        self.current_opponent_name = ""
        self.env = None

    def _sample_opponent(self):
        names, agents, weights = zip(*self.opponent_pool)
        idx = random.choices(range(len(names)), weights=weights, k=1)[0]
        self.current_opponent_name = names[idx]
        return agents[idx]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.expert_engine.reset()
        
        opp_agent = self._sample_opponent()
        self.kaggle_env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        self.trainer = self.kaggle_env.train([None, opp_agent])
        raw_obs = self.trainer.reset()
        self.current_obs = raw_obs
        return self._extract_features(raw_obs), {}

    def step(self, action):
        expert_action = self.expert_engine.act(self.current_obs, macro_action=int(action))
        raw_obs, reward, done, info = self.trainer.step(expert_action)
        self.current_obs = raw_obs

        # Calculate differential step reward
        p0_cash = float(raw_obs.get("farms", [{}])[0].get("money", 0))
        p1_cash = float(raw_obs.get("farms", [{}])[1].get("money", 0))
        cash_margin = (p0_cash - p1_cash) / 1000.0  # Scaled cash advantage in $k

        # Small dense shaping + terminal bonus
        step_reward = 0.01 * cash_margin
        if done:
            step_reward += (cash_margin * 0.1)

        obs_dict = self._extract_features(raw_obs)
        truncated = False
        return obs_dict, step_reward, done, truncated, {"margin": p0_cash - p1_cash, "opp": self.current_opponent_name}

    def _extract_features(self, raw_obs):
        player_id = raw_obs.get("player", 0)
        farms = raw_obs.get("farms", [])
        my_farm = farms[player_id] if len(farms) > player_id else {}
        opp_farm = farms[1 - player_id] if len(farms) > 1 - player_id else {}
        
        my_cash = float(my_farm.get("money", 0))
        opp_cash = float(opp_farm.get("money", 0))
        day = float(raw_obs.get("day", 0))
        step = float(raw_obs.get("step", 0))
        hour = float(raw_obs.get("hour", 0))

        # 1. Economic vector (18 features)
        market = raw_obs.get("market", {})
        prices = market.get("prices", {})
        inventory = market.get("inventory", {})

        p_wheat = float(prices.get("WHEAT", 10))
        p_melon = float(prices.get("MELON", 55))
        p_straw = float(prices.get("STRAWBERRY", 24))
        p_milk = float(prices.get("MILK", 42))
        p_wool = float(prices.get("WOOL", 70))

        inv_wheat = float(inventory.get("WHEAT", 0)) / 100.0
        inv_melon = float(inventory.get("MELON", 0)) / 100.0
        inv_straw = float(inventory.get("STRAWBERRY", 0)) / 100.0
        inv_milk = float(inventory.get("MILK", 0)) / 100.0
        inv_wool = float(inventory.get("WOOL", 0)) / 100.0

        my_lands = float(len(my_farm.get("unlocked_quadrants", ["NW"])))
        opp_lands = float(len(opp_farm.get("unlocked_quadrants", ["NW"])))
        my_hands = float(len(my_farm.get("hands", [])))
        opp_hands = float(len(opp_farm.get("hands", [])))

        economy_vec = np.array([
            my_cash / 10000.0,
            opp_cash / 10000.0,
            (my_cash - opp_cash) / 10000.0,
            day / 30.0,
            step / 720.0,
            hour / 24.0,
            p_wheat / 20.0,
            p_melon / 60.0,
            p_straw / 30.0,
            p_milk / 50.0,
            p_wool / 80.0,
            inv_wheat,
            inv_melon,
            inv_straw,
            inv_milk,
            inv_wool,
            my_lands / 4.0,
            opp_lands / 4.0,
        ], dtype=np.float32)

        # 2. Spatial grid (5 channels x 10 x 10)
        spatial_grid = np.zeros((5, 10, 10), dtype=np.float32)
        tiles = my_farm.get("tiles", [])
        for r in range(min(10, len(tiles))):
            for c in range(min(10, len(tiles[r]))):
                tile = tiles[r][c]
                if tile == "LOCKED":
                    spatial_grid[0, r, c] = 1.0
                elif isinstance(tile, dict):
                    kind = tile.get("kind")
                    if kind == "WEED":
                        spatial_grid[1, r, c] = 1.0
                    elif kind == "PLANT":
                        spatial_grid[2, r, c] = float(tile.get("yield_units", 1))
                    elif kind in ("COOP", "PASTURE"):
                        spatial_grid[3, r, c] = 1.0 if tile.get("animal") else 0.5

        # Workers presence
        fx, fy = my_farm.get("farmer", [0, 0])
        if 0 <= fy < 10 and 0 <= fx < 10:
            spatial_grid[4, fy, fx] = 1.0
        for hx, hy in my_farm.get("hands", []):
            if 0 <= hy < 10 and 0 <= hx < 10:
                spatial_grid[4, hy, hx] = 0.5

        return {"economy": economy_vec, "spatial": spatial_grid}


# ---------------------------------------------------------------------------
# 3. LOGGING CALLBACK
# ---------------------------------------------------------------------------
class PSROTrainingCallback(BaseCallback):
    def __init__(self, check_freq=720, verbose=1):
        super(PSROTrainingCallback, self).__init__(verbose)
        self.check_freq = check_freq

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            print(f"[Step {self.n_calls:,}] Rollout complete. Updating PPO policy...")
        return True


# ---------------------------------------------------------------------------
# 4. MAIN TRAINING LAUNCHER
# ---------------------------------------------------------------------------
def train_psro_oracle(
    total_timesteps: int = 7200,
    learning_rate: float = 1e-4,
    pretrained_weights: str = "neurosymbolic_cfo_weights.zip",
    save_path: str = "psro_oracle_weights.zip"
):
    print("=" * 75)
    print("🧠 PSRO BEST-RESPONSE NEURAL POLICY TRAINING PIPELINE")
    print("=" * 75)
    print(f"  * Total Timesteps:      {total_timesteps:,} turns (~{total_timesteps//720} full games)")
    print(f"  * Learning Rate:        {learning_rate}")
    print(f"  * Pretrained Checkpoint: {pretrained_weights}")
    print(f"  * Output Checkpoint:    {save_path}")
    print("-" * 75)

    env = PSROPopulationEnv()

    policy_kwargs = dict(
        features_extractor_class=HybridCNNFeaturesExtractor,
        features_extractor_kwargs=dict(features_dim=128),
        net_arch=dict(pi=[64], vf=[64])
    )

    if os.path.exists(pretrained_weights):
        print(f"[+] Loading existing weights from: {pretrained_weights}")
        model = PPO.load(
            pretrained_weights,
            env=env,
            learning_rate=learning_rate,
            ent_coef=0.01,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
    else:
        print("[*] Initializing fresh Hybrid CNN+MLP PPO model...")
        model = PPO(
            "MultiInputPolicy",
            env,
            learning_rate=learning_rate,
            n_steps=720,
            batch_size=72,
            n_epochs=5,
            gamma=0.99,
            ent_coef=0.01,
            policy_kwargs=policy_kwargs,
            verbose=1,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )

    print(f"\n🚀 Training on Device: {model.device}")
    print("Opponent Pool Mixture:")
    for name, _, weight in env.opponent_pool:
        print(f"  - {name:<20}: {weight*100:.0f}% frequency")
    print("-" * 75)

    callback = PSROTrainingCallback(check_freq=720)
    model.learn(total_timesteps=total_timesteps, callback=callback)

    model.save(save_path)
    print("\n" + "=" * 75)
    print(f"✅ PSRO Oracle Training Finished! Saved weights to: {save_path}")
    print("=" * 75)


if __name__ == "__main__":
    train_psro_oracle(
        total_timesteps=7200,     # 10 full 720-step matches
        learning_rate=1e-4,       # Fine-tuning rate to avoid catastrophic forgetting
        pretrained_weights="neurosymbolic_cfo_weights.zip",
        save_path="psro_oracle_weights.zip"
    )
