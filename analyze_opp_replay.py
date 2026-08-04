import json

with open("replays/episode-89862359-replay.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect opponent purchases, land unlocks, builds, animals, crops
opp_buys = {}
opp_lands = 0
opp_animals = 0
opp_coops = 0
opp_pastures = 0

for step_idx, step in enumerate(steps):
    s0 = step[0]
    s1 = step[1]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    
    act1 = s1.get("action")
    if act1 and isinstance(act1, dict):
        m_orders = act1.get("market", [])
        for o in m_orders:
            if o[0] == "BUY_LAND":
                print(f"[Day {day} H{hour}] Opponent BOUGHT LAND! Unlocked quads: {farms[1]['unlocked_quadrants']}")
            elif o[0] == "BUY_ANIMAL":
                print(f"[Day {day} H{hour}] Opponent BOUGHT ANIMAL: {o}")
            elif o[0] == "BUY_SEED":
                opp_buys[o[1]] = opp_buys.get(o[1], 0) + o[2]
            elif o[0] == "BUY_PRODUCT":
                print(f"[Day {day} H{hour}] Opponent BOUGHT PRODUCT: {o}")

print("\nOpponent Total Seed Buys:")
for k, v in opp_buys.items():
    print(f"  {k}: {v}")

print("\nOur Final Money:", steps[-1][0].get("reward"))
print("Opponent Final Money:", steps[-1][1].get("reward"))
