import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect Day 10 completely
print("=== DAY 10 COMPLETE TRACE ===")
for step_idx in range(len(steps)):
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    
    if day == 10:
        act0 = s0.get("action", {})
        m = act0.get("market", [])
        f = act0.get("farmer", [])
        h = act0.get("hands", [])
        
        # Summary of actions this hour
        ops = []
        if m: ops.append(f"Market: {m}")
        all_u = [f] + h
        hands_list = farms[0].get("hands", [])
        for i, u in enumerate(all_u):
            if u and u[0] not in ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]:
                pos = farms[0]["farmer"] if i == 0 else (hands_list[i-1] if (i-1) < len(hands_list) else '?')
                ops.append(f"U{i}@{pos}:{u}")
        print(f"[H{hour:02d}] Money: ${farms[0]['money']:,.0f} | Hands: {len(h)} | " + " | ".join(ops))
