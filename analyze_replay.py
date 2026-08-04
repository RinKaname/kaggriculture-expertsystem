import json

with open("replays/episode-89862973-replay.json", "r") as f:
    data = json.load(f)

steps = data.get("steps", [])
print(f"Total steps in replay: {len(steps)}")

# Player 0 and Player 1 actions and state over time
p0_actions = []
p1_actions = []
market_history = []

for step_idx, step in enumerate(steps):
    # Step has 2 player states
    s0 = step[0]
    s1 = step[1]
    obs = s0.get("observation", {})
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    farms = obs.get("farms", [])
    
    # Check actions taken
    act0 = s0.get("action")
    act1 = s1.get("action")
    
    # Check what P1 (opponent) bought in market
    if act1 and isinstance(act1, dict):
        m_orders = act1.get("market", [])
        if m_orders:
            for o in m_orders:
                print(f"[Day {day:02d} H{hour:02d}] Opponent Market Order: {o} | Opp Money: ${farms[1]['money']}")
        f_op = act1.get("farmer")
        if f_op and f_op[0] in ["BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER", "BUY_ANIMAL"]:
            print(f"[Day {day:02d} H{hour:02d}] Opponent Farmer Op: {f_op}")
        hands_ops = act1.get("hands", [])
        for h_idx, h_op in enumerate(hands_ops):
            if h_op and h_op[0] in ["BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER"]:
                print(f"[Day {day:02d} H{hour:02d}] Opponent Hand #{h_idx} Op: {h_op}")

print("\nFinal Result:")
print("Player 0 (Us):", steps[-1][0].get("reward"))
print("Player 1 (Opponent):", steps[-1][1].get("reward"))
