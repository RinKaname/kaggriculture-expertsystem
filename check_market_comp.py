import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect Day 0 turn by turn for BOTH players:
for step_idx in range(24):
    s0 = steps[step_idx][0]
    s1 = steps[step_idx][1]
    
    act0 = s0.get("action", {})
    act1 = s1.get("action", {})
    
    m0 = act0.get("market", [])
    m1 = act1.get("market", [])
    
    f0 = s0.get("observation", {}).get("farms", [{}, {}])[0]
    f1 = s0.get("observation", {}).get("farms", [{}, {}])[1]
    
    print(f"[D00 H{step_idx:02d}] P0 (${f0.get('money', 0):<5,.0f}) Orders: {m0} | P1 (${f1.get('money', 0):<5,.0f}) Orders: {m1}")
