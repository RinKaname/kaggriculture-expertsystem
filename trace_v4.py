from kaggle_environments import make
from test_apex_grandmaster_v4 import ApexGrandmasterAgentV4

agent_obj = ApexGrandmasterAgentV4()
env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run([lambda obs: agent_obj.act(obs), "starter"])

print(f"Total steps: {len(env.steps)}")
for s_idx in range(0, 720, 24):
    st = env.steps[s_idx]
    f0 = st[0].observation["farms"][0]
    p0 = st[0].observation["private"]
    print(f"Day {s_idx//24:02d}: Money: ${f0['money']:<7,.0f} | Hands: {len(f0['hands'])} | Shed: {p0.get('shed')}")
