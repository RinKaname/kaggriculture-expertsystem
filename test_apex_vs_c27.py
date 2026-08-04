from kaggle_environments import make
import apex_agent
import agent_c27
import time

print("=" * 60)
print("HEAD-TO-HEAD: Apex Agent vs c27 (8 Games, Both Seats)")
print("=" * 60)

seeds = [0, 42, 100, 2024]
results = []

for s in seeds:
    # Seat 0: Apex as P0, c27 as P1
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": s}, debug=False)
    env.run([apex_agent.agent, agent_c27.agent])
    f = env.steps[-1]
    p0_score, p1_score = f[0].reward, f[1].reward
    win = "WIN (+$" + f"{p0_score - p1_score:,})" if p0_score > p1_score else "LOSS (-$" + f"{p1_score - p0_score:,})"
    print(f"Seed {s:4d} | P0 (Apex): ${p0_score:,.0f} vs P1 (c27): ${p1_score:,.0f} -> {win}")
    results.append(p0_score > p1_score)

    # Seat 1: c27 as P0, Apex as P1
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": s}, debug=False)
    env.run([agent_c27.agent, apex_agent.agent])
    f = env.steps[-1]
    p0_score, p1_score = f[0].reward, f[1].reward
    win = "WIN (+$" + f"{p1_score - p0_score:,})" if p1_score > p0_score else "LOSS (-$" + f"{p0_score - p1_score:,})"
    print(f"Seed {s:4d} | P1 (Apex): ${p1_score:,.0f} vs P0 (c27): ${p0_score:,.0f} -> {win}")
    results.append(p1_score > p0_score)

wins = sum(results)
print("=" * 60)
print(f"TOTAL RECORD: {wins} Wins / {len(results) - wins} Losses (Win Rate: {wins/len(results)*100:.1f}%)")
print("=" * 60)
