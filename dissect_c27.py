import json
import base64
import zlib
from collections import defaultdict

with open('agent_c27.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
trace_match = re.search(r'_TRACE\s*=\s*json\.loads\(zlib\.decompress\(base64\.b85decode\(\s*\'(.*?)\'\s*\)\)\.decode\("utf-8"\)\)', content, re.DOTALL)
if trace_match:
    b85_str = trace_match.group(1).replace('\n', '').replace(' ', '').replace("'", "")
    trace_raw = zlib.decompress(base64.b85decode(b85_str)).decode("utf-8")
    trace = json.loads(trace_raw)
    print(f"Total turns in trace: {len(trace)}")
    
    # Analyze trace by day (24 turns per day)
    day_summary = defaultdict(lambda: {"market": [], "farmer_ops": defaultdict(int), "num_hands": 0})
    
    for step, turn in enumerate(trace):
        day = step // 24
        hour = step % 24
        market = turn.get("market", [])
        farmer = turn.get("farmer", ["PASS"])
        hands = turn.get("hands", [])
        
        day_summary[day]["num_hands"] = max(day_summary[day]["num_hands"], len(hands))
        if market:
            day_summary[day]["market"].extend(market)
        day_summary[day]["farmer_ops"][farmer[0]] += 1

    print("\n--- DAY-BY-DAY ECONOMIC TRACE BREAKDOWN ---")
    for day in range(30):
        m = day_summary[day]["market"]
        hands = day_summary[day]["num_hands"]
        # summarize market orders
        orders_summary = defaultdict(int)
        for order in m:
            if isinstance(order, list) and len(order) >= 2:
                op = order[0]
                item = order[1] if len(order) > 1 else ""
                qty = order[2] if len(order) > 2 else 1
                orders_summary[f"{op} {item}"] += qty
            elif isinstance(order, list) and len(order) == 1:
                orders_summary[order[0]] += 1
        
        orders_str = ", ".join([f"{k}x{v}" for k, v in orders_summary.items()])
        print(f"Day {day:02d} | Hands: {hands:2d} | Market: {orders_str}")
