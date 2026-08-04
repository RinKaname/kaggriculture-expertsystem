"""
Self-Play Benchmark:
Apex Grandmaster V3 vs Previous Paced Selling Agent (43k-46k)
"""
from kaggle_environments import make
from test_apex_grandmaster import agent as apex_agent
from main import agent as prev_agent

print("=" * 60)
print("HEAD-TO-HEAD MATCHUP: Apex Grandmaster vs Previous Main")
print("=" * 60)

for g in range(4):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    if g % 2 == 0:
        env.run([apex_agent, prev_agent])
        s0 = env.steps[-1][0].reward
        s1 = env.steps[-1][1].reward
        print(f"Match {g+1} (Apex as P0): Apex=${s0:,.0f} vs Prev=${s1:,.0f} | Winner: {'APEX' if s0 > s1 else 'PREV'}")
    else:
        env.run([prev_agent, apex_agent])
        s0 = env.steps[-1][0].reward
        s1 = env.steps[-1][1].reward
        print(f"Match {g+1} (Apex as P1): Prev=${s0:,.0f} vs Apex=${s1:,.0f} | Winner: {'APEX' if s1 > s0 else 'PREV'}")
