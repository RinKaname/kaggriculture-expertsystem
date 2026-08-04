from kaggle_environments import make
from test_apex_grandmaster import ApexGrandmasterAgentV3
from main import agent as prev_agent

def make_apex_agent():
    agent_obj = ApexGrandmasterAgentV3()
    def _act(obs):
        return agent_obj.act(obs)
    return _act

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run([make_apex_agent(), prev_agent])

print(f"Total steps in game: {len(env.steps)}")
for s_idx in [0, 24, 48, 120, 240, 360, 480, 600, 719]:
    st = env.steps[s_idx]
    s0, s1 = st[0], st[1]
    f0 = s0.observation["farms"][0]
    p0 = s0.observation["private"]
    print(f"Step {s_idx:03d} (Day {s_idx//24}): P0 Money: ${f0['money']:,.0f} | Hands: {len(f0['hands'])} | Shed: {p0.get('shed')} | P1 Money: ${s1.observation['farms'][1]['money']:,.0f}")
