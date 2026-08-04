import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect fertilizing actions: when and how are crops fertilized in 130k replay?
fert_actions = []
for step_idx in range(len(steps)):
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    if not farms: continue
    
    act0 = s0.get("action", {})
    if not act0: continue
    f = act0.get("farmer", [])
    h = act0.get("hands", [])
    all_u = [f] + h
    hands_list = farms[0].get("hands", [])
    for i, u in enumerate(all_u):
        if u and u[0] == "FERTILIZE":
            pos = farms[0]["farmer"] if i == 0 else (hands_list[i-1] if (i-1) < len(hands_list) else '?')
            fert_actions.append((day, hour, i, pos))

print(f"Total FERTILIZE actions: {len(fert_actions)}")
print("Sample FERTILIZE actions:")
for a in fert_actions[:25]:
    print(f"[Day {a[0]:02d} H{a[1]:02d}] Unit {a[2]} at {a[3]}")
