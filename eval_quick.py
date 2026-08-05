from kaggle_environments import make
import test_upgraded_agent
import agent_c27
import time

print("--- Testing Upgraded Expert Agent vs Starter (Seed 0) ---")
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
env.run([test_upgraded_agent.agent, "starter"])
final = env.steps[-1]
print(f"My Score: ${final[0].reward:,} | Starter Score: ${final[1].reward:,}")

print("\n--- Testing Upgraded Expert Agent vs c27 (Seed 0) ---")
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
env.run([test_upgraded_agent.agent, agent_c27.agent])
final = env.steps[-1]
print(f"My Score: ${final[0].reward:,} | c27 Score: ${final[1].reward:,}")
