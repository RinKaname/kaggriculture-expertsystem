"""Unit test for MultiExpertSystem and KaggricultureNeurosymbolicEnv."""
import sys
import os
import numpy as np

from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv, NUM_MACRO_ACTIONS
from src.multi_expert_engine import MultiExpertSystem

def test_multi_expert_engine():
    print("[*] Testing MultiExpertSystem instantiation & action generation...")
    engine = MultiExpertSystem()
    engine.reset()
    
    # Dummy Kaggle observation
    dummy_obs = {
        "player": 0,
        "step": 0,
        "day": 0,
        "hour": 0,
        "farms": [
            {"money": 3000, "farmer": [0, 0], "hands": [], "tiles": [[None]*10 for _ in range(10)], "unlocked_quadrants": ["NW"]},
            {"money": 3000, "farmer": [0, 0], "hands": [], "tiles": [[None]*10 for _ in range(10)], "unlocked_quadrants": ["NW"]}
        ],
        "market": {"prices": {"MELON": 250, "STRAWBERRY": 120, "MILK": 160, "WOOL": 200}},
        "private": {"shed": {}, "seeds": {}}
    }
    
    for action_idx in range(NUM_MACRO_ACTIONS):
        act = engine.act(dummy_obs, macro_action=action_idx)
        assert isinstance(act, dict), f"Action {action_idx} did not return a dict"
        assert "farmer" in act, f"Action {action_idx} missing 'farmer'"
        assert "market" in act, f"Action {action_idx} missing 'market'"
        print(f" -> Macro Action {action_idx} returned: {act['farmer']} | Market orders: {len(act['market'])}")
        
    print("[+] MultiExpertSystem unit test passed!\n")

def test_gym_environment():
    print("[*] Testing KaggricultureNeurosymbolicEnv Gym interface...")
    env = KaggricultureNeurosymbolicEnv(opponent="starter")
    obs, info = env.reset()
    
    assert "economy" in obs, "Obs missing economy"
    assert "spatial" in obs, "Obs missing spatial"
    assert obs["economy"].shape == (18,), f"Unexpected economy shape: {obs['economy'].shape}"
    assert obs["spatial"].shape == (5, 10, 10), f"Unexpected spatial shape: {obs['spatial'].shape}"
    print(f" -> Initial Economy: Cash=${obs['economy'][2]:,.0f} | Opp Cash=${obs['economy'][3]:,.0f}")
    
    # Step 1: Execute Action 0 (Elite Tape)
    obs, reward, done, truncated, info = env.step(0)
    print(f" -> Day 0 Step (Action 0 - Elite Tape) -> Reward: {reward:+.3f} | Done: {done}")
    
    # Step 2: Execute Action 1 (Melon IPO)
    obs, reward, done, truncated, info = env.step(1)
    print(f" -> Day 1 Step (Action 1 - Melon IPO) -> Reward: {reward:+.3f} | Done: {done}")
    
    print("[+] Gym Environment unit test passed!\n")

if __name__ == "__main__":
    test_multi_expert_engine()
    test_gym_environment()
