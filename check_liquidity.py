import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect Day 0 to Day 7 in detail: what did the 130k bot buy and sell in the market each day?
for step_idx in range(0, 7*24):
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    
    act0 = s0.get("action", {})
    m = act0.get("market", [])
    if m:
        print(f"[D{day:02d} H{hour:02d}] Money: ${farms[0]['money']:<6,.0f} | Orders: {m}")
