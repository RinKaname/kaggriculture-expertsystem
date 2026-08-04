import json
import glob

files = ["replays/89860059.json", "replays/89862408.json"]

for fpath in files:
    print("=" * 70)
    print(f"ANALYZING TOP REPLAY: {fpath}")
    print("=" * 70)
    with open(fpath, "r") as f:
        data = json.load(f)
    
    steps = data.get("steps", [])
    print(f"Total steps: {len(steps)}")
    
    final_s0 = steps[-1][0]
    final_s1 = steps[-1][1]
    print(f"Final Score P0: {final_s0.get('reward'):,.2f} | Status: {final_s0.get('status')}")
    print(f"Final Score P1: {final_s1.get('reward'):,.2f} | Status: {final_s1.get('status')}")
    
    for p_idx in [0, 1]:
        print(f"\n--- PLAYER {p_idx} DETAILED STRATEGY ---")
        seed_buys = {}
        prod_buys = {}
        animal_buys = {}
        structure_builds = {}
        lands_bought = []
        sales_by_item = {}
        hires_by_day = {}
        actions_count = {}
        
        for step_idx, step in enumerate(steps):
            s = step[p_idx]
            obs = s.get("observation", {})
            day = obs.get("day", 0)
            hour = obs.get("hour", 0)
            farms = obs.get("farms", [])
            
            act = s.get("action")
            if not act or not isinstance(act, dict):
                continue
                
            # Market orders
            for order in act.get("market", []):
                op = order[0]
                if op == "BUY_LAND":
                    unlocked = farms[p_idx]["unlocked_quadrants"] if farms else []
                    lands_bought.append((day, hour, unlocked))
                elif op == "BUY_SEED":
                    crop, n = order[1], order[2]
                    seed_buys[crop] = seed_buys.get(crop, 0) + n
                elif op == "BUY_PRODUCT":
                    item, n = order[1], order[2]
                    prod_buys[item] = prod_buys.get(item, 0) + n
                elif op == "BUY_ANIMAL":
                    animal, n = order[1], order[2]
                    animal_buys[animal] = animal_buys.get(animal, 0) + n
                elif op == "SELL":
                    item, n = order[1], order[2]
                    sales_by_item[item] = sales_by_item.get(item, 0) + n
                elif op == "HIRE":
                    hires_by_day[day] = hires_by_day.get(day, 0) + 1
            
            # Unit actions (farmer + hands)
            all_unit_acts = [act.get("farmer")] + act.get("hands", [])
            for u_act in all_unit_acts:
                if not u_act or not isinstance(u_act, list):
                    continue
                op = u_act[0]
                actions_count[op] = actions_count.get(op, 0) + 1
                if op in ["BUILD_COOP", "BUILD_PASTURE"]:
                    structure_builds[(day, hour, op)] = structure_builds.get((day, hour, op), 0) + 1
                    
        print(f"Land Purchases: {lands_bought}")
        print(f"Total Hires by Day Sample: {[f'D{d}:{h}' for d,h in list(hires_by_day.items())[:8]]} ... total hires: {sum(hires_by_day.values())}")
        print(f"Total Seed Buys: {seed_buys}")
        print(f"Total Product Buys: {prod_buys}")
        print(f"Total Animal Buys: {animal_buys}")
        print(f"Structures Built: {structure_builds}")
        print(f"Total Sales by Item: {sales_by_item}")
        print(f"Unit Operations Breakdown: {actions_count}")

