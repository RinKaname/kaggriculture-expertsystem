import main
import Archive.baseline2 as baseline2
from kaggle_environments import make

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run([main.agent, baseline2.agent])

print("\n=== TURN-BY-TURN CASH & STATUS LOG ===")
for day in [0, 5, 10, 15, 20, 25, 29]:
    step = min(719, day * 24 + 23)
    s = env.steps[step]
    f0 = s[0]["observation"]["farms"][0]
    f1 = s[0]["observation"]["farms"][1]
    p0_shed = s[0]["observation"]["private"]["shed"]
    p1_shed = s[1]["observation"]["private"]["shed"]
    
    print(f"Day {day:02d}:")
    print(f"  Main.py:       Money: ${f0['money']:>7,.0f} | Quads: {f0['unlocked_quadrants']} | Hands: {len(f0['hands'])} | Shed: {p0_shed}")
    print(f"  Baseline2.py:  Money: ${f1['money']:>7,.0f} | Quads: {f1['unlocked_quadrants']} | Hands: {len(f1['hands'])} | Shed: {p1_shed}")

final = env.steps[-1]
print(f"\nFINAL: Main: ${final[0]['reward']:,} vs Baseline2: ${final[1]['reward']:,}")
