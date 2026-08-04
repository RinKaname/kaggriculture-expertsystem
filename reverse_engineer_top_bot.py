import json

with open("replays/89862408.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])

# Let's inspect Day 0 to Day 5 step by step for Player 0
print("=== DAY 0 TO 5 DETAILED TIMELINE ===")
for step_idx in range(min(120, len(steps))):
    s = steps[step_idx][0]
    obs = s.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    my_farm = farms[0] if farms else {}
    
    act = s.get("action")
    if not act:
        continue
    
    m_orders = act.get("market", [])
    f_act = act.get("farmer", [])
    h_acts = act.get("hands", [])
    
    # Print interesting actions
    events = []
    if m_orders:
        events.append(f"Market: {m_orders}")
    if f_act and f_act[0] not in ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]:
        events.append(f"Farmer({my_farm.get('farmer')}): {f_act}")
    for h_i, h in enumerate(h_acts):
        if h and h[0] not in ["PASS", "NORTH", "SOUTH", "EAST", "WEST"]:
            events.append(f"Hand{h_i}({my_farm.get('hands', [])[h_i] if h_i < len(my_farm.get('hands', [])) else '?' }): {h}")
            
    if events or hour == 0:
        print(f"[Day {day:02d} H{hour:02d}] Money: ${my_farm.get('money', 0):,.0f} | Hands: {len(my_farm.get('hands', []))} | " + " | ".join(events))
