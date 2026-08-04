import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

print(f"Total steps: {len(steps)}")

for day in range(30):
    step_idx = day * 24 + 1  # hour 1
    if step_idx >= len(steps):
        break
    s0 = steps[step_idx][0]
    obs = s0.get("observation", {})
    farms = obs.get("farms", [{}, {}])
    f0 = farms[0]
    p0 = obs.get("private", {})
    
    # Check unlocked quads
    quads = f0.get("unlocked_quadrants", [])
    money = f0.get("money", 0)
    tiles = f0.get("tiles", [])
    
    crops = {}
    animals = {}
    for r in tiles:
        for t in r:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    c = t.get("crop")
                    crops[c] = crops.get(c, 0) + 1
                elif "animal" in t:
                    a = t.get("animal")
                    animals[a] = animals.get(a, 0) + 1
                    
    print(f"Day {day:02d} (H01): Money: ${money:<7,.0f} | Quads: {quads} | Animals: {animals} | Crops: {crops}")
