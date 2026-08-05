"""Head-to-head tournament test: agent_apex_v2.py vs main.py (Kaggriculture-AgriSchemer-V1)."""
from kaggle_environments import make
import main
import agent_apex_v2

print("=" * 65)
print("HEAD-TO-HEAD TOURNAMENT: Apex V2 vs Main (AgriSchemer-V1)")
print("=" * 65)

# Game 1: Apex V2 as Player 0 vs Main as Player 1
print("\n--- Match 1: Apex V2 (P0) vs Main V1 (P1) ---")
env1 = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env1.run([agent_apex_v2.agent, main.agent])
r0 = env1.steps[-1][0].reward
r1 = env1.steps[-1][1].reward
print(f"Apex V2 (P0): ${r0:,.0f}")
print(f"Main V1 (P1): ${r1:,.0f}")
diff1 = r0 - r1
print(f"Winner: {'Apex V2' if diff1 > 0 else 'Main V1'} by ${abs(diff1):,.0f}")

# Game 2: Main as Player 0 vs Apex V2 as Player 1
print("\n--- Match 2: Main V1 (P0) vs Apex V2 (P1) ---")
env2 = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env2.run([main.agent, agent_apex_v2.agent])
r0_2 = env2.steps[-1][0].reward
r1_2 = env2.steps[-1][1].reward
print(f"Main V1 (P0): ${r0_2:,.0f}")
print(f"Apex V2 (P1): ${r1_2:,.0f}")
diff2 = r1_2 - r0_2
print(f"Winner: {'Apex V2' if diff2 > 0 else 'Main V1'} by ${abs(diff2):,.0f}")

print("\n" + "=" * 65)
print(f"SUMMARY: Apex V2 Net Advantage = ${diff1 + diff2:+,.0f}")
print("=" * 65)
