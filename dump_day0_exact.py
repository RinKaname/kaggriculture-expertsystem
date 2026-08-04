import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

print("=== EXACT DAY 0 & DAY 1 ACTIONS ===")
for step_idx in range(48):
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    priv = obs.get("private", {})
    farm = farms[0]
    
    act0 = s0.get("action", {})
    m = act0.get("market", [])
    f = act0.get("farmer", [])
    h = act0.get("hands", [])
    
    # Farmer & Hand positions
    f_pos = farm["farmer"]
    h_pos = farm["hands"]
    
    print(f"[D{day:02d} H{hour:02d}] Money: ${farm['money']:<6,.0f} | Mkt: {m} | F@{f_pos}: {f} | Hands({len(h)}): {list(zip(h_pos, h))}")
