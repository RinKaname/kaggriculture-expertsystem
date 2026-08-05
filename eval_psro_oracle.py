"""Evaluate the newly trained PSRO Oracle model against Grandmaster Opponents."""
import os
import sys
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from kaggle_environments import make

from src.multi_expert_engine import MultiExpertSystem
from src.subin_an_tape import agent as subin_agent
from Archive.baseline import agent as baseline_agent
from train_psro_oracle import HybridCNNFeaturesExtractor, PSROPopulationEnv


def make_neural_agent(model_path="psro_oracle_weights.zip"):
    dummy_env = PSROPopulationEnv()
    model = PPO.load(model_path, env=dummy_env, device="cpu")
    expert_engine = MultiExpertSystem()

    def neural_agent(obs):
        # Extract features
        features = dummy_env._extract_features(obs)
        # Predict macro-action
        action, _ = model.predict(features, deterministic=True)
        # Execute through multi-expert engine
        return expert_engine.act(obs, macro_action=int(action))

    return neural_agent


def evaluate_matches():
    print("=" * 75)
    print("[*] EVALUATING PSRO NEURAL ORACLE AGAINST BENCHMARK OPPONENTS")
    print("=" * 75)

    neural_agent = make_neural_agent("psro_oracle_weights.zip")

    opponents = [
        ("Starter", "starter"),
        ("Apex Baseline", baseline_agent),
        ("Subin An Moon V14", subin_agent),
        ("Main V1 ($182k Tape)", "main.py"),
    ]

    for name, opp in opponents:
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        env.run([neural_agent, opp])
        
        p0_final = env.steps[-1][0].reward or 0
        p1_final = env.steps[-1][1].reward or 0
        margin = p0_final - p1_final
        win_status = "[WIN]" if margin > 0 else ("[TIE]" if margin == 0 else "[LOSS]")

        print(f"vs {name:<22} | Neural: ${p0_final:>8,.0f} | Opp: ${p1_final:>8,.0f} | Margin: {margin:>+9,.0f} | {win_status}")

    print("=" * 75)



if __name__ == "__main__":
    evaluate_matches()
