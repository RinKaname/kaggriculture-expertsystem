from kaggle_environments import make
from main import agent as my_agent

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run([my_agent, "starter"])

for step_num in range(0, min(48, len(env.steps))):
    step_data = env.steps[step_num]
    p0 = step_data[0]
    obs = p0.observation
    act = p0.action
    farm = obs.farms[0]
    priv = obs.private
    print(f"Step {step_num:03d} (D{obs.day} H{obs.hour}): Money=${farm['money']:.0f} Farmer={farm['farmer']} Hands={len(farm['hands'])} Action={act} Shed={priv.get('shed')} Seeds={priv.get('seeds')}")

