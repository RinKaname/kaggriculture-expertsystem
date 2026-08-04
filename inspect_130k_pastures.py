import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect where P0 builds pastures, what animals are bought when, and how workers are assigned
pasture_positions = []
animal_purchases = []
land_purchases = []

for step_idx, step in enumerate(steps):
    s0 = step[0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    
    act0 = s0.get("action")
    if not act0:
        continue
    
    # Check builds
    all_units = [act0.get("farmer")] + act0.get("hands", [])
    for u_idx, u in enumerate(all_units):
        if u and u[0] in ["BUILD_PASTURE", "BUILD_COOP", "PLACE"]:
            u_pos = farms[0]["farmer"] if u_idx == 0 else farms[0]["hands"][u_idx - 1]
            print(f"[Day {day:02d} H{hour:02d}] Unit {u_idx} at {u_pos}: {u}")
            
    for m in act0.get("market", []):
        if m[0] in ["BUY_ANIMAL", "BUY_LAND"]:
            print(f"[Day {day:02d} H{hour:02d}] Market: {m} | Money: ${farms[0]['money']}")
