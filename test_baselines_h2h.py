import Archive.baseline as baseline1
import Archive.baseline2 as baseline2
from kaggle_environments import make

print("=== HEAD TO HEAD: baseline1 vs baseline2 (6 Games) ===")
scores1 = []
scores2 = []

for g in range(6):
    as_p0 = (g % 2 == 0)
    agents = [baseline1.agent, baseline2.agent] if as_p0 else [baseline2.agent, baseline1.agent]
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.run(agents)
    r0 = env.steps[-1][0]["reward"] or 0
    r1 = env.steps[-1][1]["reward"] or 0
    s1 = r0 if as_p0 else r1
    s2 = r1 if as_p0 else r0
    scores1.append(s1)
    scores2.append(s2)
    winner = "Baseline1 (V1)" if s1 > s2 else ("Baseline2 (V2)" if s2 > s1 else "DRAW")
    print(f"Game {g+1:02d}: {winner:<16} | Baseline1: ${s1:,.0f} vs Baseline2: ${s2:,.0f}")

print(f"\nAvg Baseline1 (V1): ${sum(scores1)/len(scores1):,.2f}")
print(f"Avg Baseline2 (V2): ${sum(scores2)/len(scores2):,.2f}")
