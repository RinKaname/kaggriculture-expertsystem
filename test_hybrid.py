from src.neurosymbolic_env import KaggricultureNeurosymbolicEnv
env = KaggricultureNeurosymbolicEnv(opponent="main.py")
obs = env.reset()
print("Initial obs extracted.")

done = False
steps = 0
while not done and steps < 2:
    action = env.action_space.sample()
    obs, reward, done, truncated, info = env.step(action)
    steps += 1
    print(f"Step {steps}: economy shape={obs['economy'].shape}, spatial shape={obs['spatial'].shape}, Unlocked Sum={obs['spatial'][0, :, :].sum()}")

print("Hybrid environment stepped successfully.")
