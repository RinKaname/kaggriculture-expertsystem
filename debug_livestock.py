from kaggle_environments import make
from test_livestock_agent import agent

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run([agent, "starter"])

for step_idx, step in enumerate(env.steps):
    if step_idx % 24 == 0 or step_idx == 719:
        obs0 = step[0].observation
        day = obs0.get("day", step_idx // 24)
        farm0 = obs0["farms"][0]
        money = farm0["money"]
        shed = obs0["private"]["shed"]
        active_animals = sum(1 for row in farm0["tiles"] for t in row if isinstance(t, dict) and "animal" in t)
        active_plants = sum(1 for row in farm0["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "PLANT")
        active_weeds = sum(1 for row in farm0["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "WEED")
        print(f"Day {day:02d} | Money: ${money:,.0f} | Animals: {active_animals} | Plants: {active_plants} | Weeds: {active_weeds} | Shed: {shed}")
