from kaggle_environments import make
import apex_agent
import Archive.baseline2 as baseline2
import replica

print("--- Testing Apex Agent vs Starter ---")
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
env.run([apex_agent.agent, "starter"])
f = env.steps[-1]
print(f"Apex: ${f[0].reward:,.0f} vs Starter: ${f[1].reward:,.0f} -> Win Margin: +${f[0].reward - f[1].reward:,.0f}")

print("\n--- Testing Apex Agent vs Baseline2 ---")
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
env.run([apex_agent.agent, baseline2.agent])
f = env.steps[-1]
print(f"Apex: ${f[0].reward:,.0f} vs Baseline2: ${f[1].reward:,.0f} -> Win Margin: +${f[0].reward - f[1].reward:,.0f}")

print("\n--- Testing Apex Agent vs Replica ---")
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
env.run([apex_agent.agent, replica.agent])
f = env.steps[-1]
print(f"Apex: ${f[0].reward:,.0f} vs Replica: ${f[1].reward:,.0f} -> Win Margin: +${f[0].reward - f[1].reward:,.0f}")
