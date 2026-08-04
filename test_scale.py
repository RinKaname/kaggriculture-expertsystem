import time
from kaggle_environments import make
import test_apex_grandmaster_v5
import main

print("Testing test_apex_grandmaster_v5:")
env1 = make("kaggriculture", configuration={"episodeSteps": 720})
env1.run([test_apex_grandmaster_v5.agent, "starter"])
print("V5 vs Starter Score:", env1.steps[-1][0].reward)

print("\nTesting main.py:")
env2 = make("kaggriculture", configuration={"episodeSteps": 720})
env2.run([main.agent, "starter"])
print("Main vs Starter Score:", env2.steps[-1][0].reward)
