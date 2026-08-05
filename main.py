"""PSRO-Trained Neurosymbolic Grandmaster Agent for Kaggriculture.
Combines 232k Hybrid CNN+MLP Policy Network with Grandmaster Symbolic Engines.
"""
import os
import sys
import numpy as np
import torch
import torch.nn as nn

# Ensure local imports work in Kaggle submission environment
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
sys.path.append(ROOT_DIR)

from src.multi_expert_engine import MultiExpertSystem



# ---------------------------------------------------------------------------
# 1. LIGHTWEIGHT INFERENCE ACTOR NETWORK
# ---------------------------------------------------------------------------
class LightweightActor(nn.Module):
    def __init__(self):
        super(LightweightActor, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(5, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(32 * 10 * 10, 64),
            nn.ReLU()
        )
        self.mlp = nn.Sequential(
            nn.Linear(18, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU()
        )
        self.policy_net = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU()
        )
        self.action_net = nn.Linear(64, 7)

    def forward(self, economy, spatial):
        spatial_feat = self.cnn(spatial)
        econ_feat = self.mlp(economy)
        features = torch.cat([spatial_feat, econ_feat], dim=1)
        latent = self.policy_net(features)
        logits = self.action_net(latent)
        return torch.argmax(logits, dim=1).item()


# ---------------------------------------------------------------------------
# 2. FEATURE EXTRACTION PIPELINE (<0.2ms)
# ---------------------------------------------------------------------------
def extract_features(raw_obs):
    player_id = raw_obs.get("player", 0)
    farms = raw_obs.get("farms", [])
    my_farm = farms[player_id] if len(farms) > player_id else {}
    opp_farm = farms[1 - player_id] if len(farms) > 1 - player_id else {}
    
    my_cash = float(my_farm.get("money", 0))
    opp_cash = float(opp_farm.get("money", 0))
    day = float(raw_obs.get("day", 0))
    step = float(raw_obs.get("step", 0))
    hour = float(raw_obs.get("hour", 0))

    # Economic vector (18 features)
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

    # Spatial grid (5 channels x 10 x 10)
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

    fx, fy = my_farm.get("farmer", [0, 0])
    if 0 <= fy < 10 and 0 <= fx < 10:
        spatial_grid[4, fy, fx] = 1.0
    for hx, hy in my_farm.get("hands", []):
        if 0 <= hy < 10 and 0 <= hx < 10:
            spatial_grid[4, hy, hx] = 0.5

    econ_tensor = torch.from_numpy(economy_vec).unsqueeze(0)
    spatial_tensor = torch.from_numpy(spatial_grid).unsqueeze(0)
    return econ_tensor, spatial_tensor


# ---------------------------------------------------------------------------
# 3. GLOBAL SINGLETON RUNTIME
# ---------------------------------------------------------------------------
_ENGINE = None
_MODEL = None


def _init_runtime():
    global _ENGINE, _MODEL
    if _ENGINE is None:
        _ENGINE = MultiExpertSystem()
    if _MODEL is None:
        _MODEL = LightweightActor()
        _MODEL.eval()
        weights_path = os.path.abspath(os.path.join(ROOT_DIR, "policy_weights.pt"))
        if os.path.exists(weights_path):
            raw_weights = torch.load(weights_path, map_location="cpu")
            mapped = {
                "cnn.0.weight": raw_weights.get("features_extractor.cnn.0.weight"),
                "cnn.0.bias": raw_weights.get("features_extractor.cnn.0.bias"),
                "cnn.2.weight": raw_weights.get("features_extractor.cnn.2.weight"),
                "cnn.2.bias": raw_weights.get("features_extractor.cnn.2.bias"),
                "cnn.5.weight": raw_weights.get("features_extractor.cnn.5.weight"),
                "cnn.5.bias": raw_weights.get("features_extractor.cnn.5.bias"),
                "mlp.0.weight": raw_weights.get("features_extractor.mlp.0.weight"),
                "mlp.0.bias": raw_weights.get("features_extractor.mlp.0.bias"),
                "mlp.2.weight": raw_weights.get("features_extractor.mlp.2.weight"),
                "mlp.2.bias": raw_weights.get("features_extractor.mlp.2.bias"),
                "policy_net.0.weight": raw_weights.get("mlp_extractor.policy_net.0.weight"),
                "policy_net.0.bias": raw_weights.get("mlp_extractor.policy_net.0.bias"),
                "action_net.weight": raw_weights.get("action_net.weight"),
                "action_net.bias": raw_weights.get("action_net.bias"),
            }
            if all(v is not None for v in mapped.values()):
                _MODEL.load_state_dict(mapped)
                print("[+] Loaded LightweightActor policy weights successfully.")



def agent(obs):
    """Kaggle submission entry point."""
    _init_runtime()
    
    # Step 0 reset
    step = int(obs.get("step", 0) or 0)
    if step == 0:
        _ENGINE.reset()

    # Neural inference
    try:
        econ, spatial = extract_features(obs)
        with torch.no_grad():
            macro_action = _MODEL(econ, spatial)
    except Exception:
        macro_action = 1  # Fallback to Subin An Moon V14 if tensor conversion fails

    # Symbolic execution
    return _ENGINE.act(obs, macro_action=macro_action)
