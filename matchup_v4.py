"""
Head-to-head validation:
Apex Grandmaster V4 vs Previous Main (43k-46k)
"""
from kaggle_environments import make
from test_apex_grandmaster_v4 import ApexGrandmasterAgentV4
from main import agent as prev_agent

print("=" * 65)
print("HEAD-TO-HEAD MATCHUP: Apex Grandmaster V4 vs Previous Main")
print("=" * 65)

for g in range(4):
    p0_obj = ApexGrandmasterAgentV4()
    p1_obj = ApexGrandmasterAgentV4()
    
    if g % 2 == 0:
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
        env.run([lambda obs: p0_obj.act(obs), prev_agent])
        s0 = env.steps[-1][0].reward
        s1 = env.steps[-1][1].reward
        print(f"Match {g+1} (Apex as P0): Apex=${s0:,.0f} vs Prev=${s1:,.0f} | Winner: {'APEX' if s0 > s1 else 'PREV'}")
    else:
        env.run([prev_agent, lambda obs: p1_obj.act(obs)])
        s0 = env.steps[-1][0].reward
        s1 = env.steps[-1][1].reward
        print(f"Match {g+1} (Apex as P1): Prev=${s0:,.0f} vs Apex=${s1:,.0f} | Winner: {'APEX' if s1 > s0 else 'PREV'}")
