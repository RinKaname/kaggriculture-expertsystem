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

s0 = env.steps[-1][0]
s1 = env.steps[-1][1]
print(f"P0 Status: {s0.status} | Reward: {s0.reward}")
print(f"P1 Status: {s1.status} | Reward: {s1.reward}")
if s0.status != "DONE":
    print(f"P0 Error Log: {s0.get('error')}")
