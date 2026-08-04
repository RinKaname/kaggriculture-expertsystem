import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect Day 1 to Day 30 economy metrics for Player 0 in the 130k replay
print(f"{'Day':<4} | {'Money':<10} | {'Hands':<6} | {'Shed Items':<45} | {'Active Plants & Animals'}")
print("-" * 90)

for step_idx in range(0, len(steps), 24):
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    farms = obs.get("farms", [])
    priv = obs.get("private", {})
    farm = farms[0] if farms else {}
    
    shed = priv.get("shed", {})
    shed_str = ", ".join(f"{k}:{v}" for k, v in shed.items() if v > 0)
    
    # count animals and crops
    c_counts = {}
    a_counts = {}
    for row in farm.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict):
                if "animal" in tile:
                    a_counts[tile["animal"]] = a_counts.get(tile["animal"], 0) + 1
                elif "crop" in tile:
                    c_counts[tile["crop"]] = c_counts.get(tile["crop"], 0) + 1
                    
    plant_str = " | ".join([f"{k}:{v}" for k,v in a_counts.items()] + [f"{k}:{v}" for k,v in c_counts.items()])
    print(f"D{day:02d}  | ${farm.get('money', 0):<9,.0f} | {len(farm.get('hands', [])):<6} | {shed_str[:43]:<45} | {plant_str}")
