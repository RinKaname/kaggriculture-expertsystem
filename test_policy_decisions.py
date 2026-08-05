import numpy as np
from stable_baselines3 import PPO
from kaggle_environments import make
from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv
from Archive.baseline import ApexGrandmasterAgent

model = PPO.load("neurosymbolic_cfo_weights.zip")
print("Model loaded successfully!")

env = KaggricultureNeurosymbolicEnv(opponent="starter")
obs, _ = env.reset()

print("\nTesting 10 decisions from trained policy:")
for step in range(10):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, trunc, info = env.step(action)
    print(f"Macro Step {step+1:2d} -> Policy Action: {action} ({env.symbolic_engine.p}) -> Reward: {reward:.2f}")
