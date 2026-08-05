from kaggle_environments import make
import main
import agent_apex_v2

env = make('kaggriculture', configuration={'episodeSteps': 720}, debug=True)
env.run([agent_apex_v2.agent, main.agent])

steps = env.steps
print(f"Final scores: P0 (Apex V2)=${steps[-1][0].reward:,} | P1 (Main V1)=${steps[-1][1].reward:,}")

sales_p0 = {}
sales_p1 = {}

for t, s in enumerate(steps):
    a0 = s[0].get('action', {})
    a1 = s[1].get('action', {})
    if isinstance(a0, dict) and a0.get('market'):
        for o in a0['market']:
            if o[0] == 'SELL':
                prod, qty = o[1], o[2]
                sales_p0[prod] = sales_p0.get(prod, 0) + qty
    if isinstance(a1, dict) and a1.get('market'):
        for o in a1['market']:
            if o[0] == 'SELL':
                prod, qty = o[1], o[2]
                sales_p1[prod] = sales_p1.get(prod, 0) + qty

print("\n--- Total Sold Units ---")
for p in sorted(set(list(sales_p0.keys()) + list(sales_p1.keys()))):
    print(f"{p:12s}: Apex V2={sales_p0.get(p, 0):5d} | Main V1={sales_p1.get(p, 0):5d}")

print("\n--- Market Price Evolution ---")
for t in range(0, 720, 48):
    obs = steps[t][0].observation
    prices = obs.get('market', {}).get('prices', {})
    m_p = prices.get('MELON')
    s_p = prices.get('STRAWBERRY')
    k_p = prices.get('MILK')
    w_p = prices.get('WOOL')
    print(f"Day {t//24:2d} (Step {t:3d}): Melon=${m_p} Straw=${s_p} Milk=${k_p} Wool=${w_p}")
