from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv
env = KaggricultureNeurosymbolicEnv(opponent="main.py")
obs, _ = env.reset()
print(f"Initial Observation: {obs}")

done = False
steps = 0
total_reward = 0
while not done and steps < 10: # Just test a few steps
    # Just take random actions to test stability
    action = env.action_space.sample()
    obs, reward, done, truncated, info = env.step(action)
    total_reward += reward
    steps += 1

print(f"Successfully simulated {steps} steps with Symbolic Engine. Final Obs: {obs}")
