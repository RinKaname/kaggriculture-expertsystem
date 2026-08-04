from kaggle_environments import make
import main

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)

# Run game step by step
obs = env.reset()

for day in range(30):
    for hour in range(24):
        step_idx = day * 24 + hour
        f0 = env.steps[-1][0].observation.farms[0]
        f1 = env.steps[-1][0].observation.farms[1]
        p0_priv = env.steps[-1][0].observation.private
        mkt = env.steps[-1][0].observation.market
        
        # Take step
        act0 = main.agent(env.steps[-1][0].observation)
        # starter agent is built in, let's let env step
        state = env.step([act0, {}])
        
    f0 = env.steps[-1][0].observation.farms[0]
    p0_priv = env.steps[-1][0].observation.private
    mkt = env.steps[-1][0].observation.market
    
    # Count plants by crop
    crops = {}
    animals = {}
    for row in f0["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    c = t.get("crop")
                    crops[c] = crops.get(c, 0) + 1
                elif "animal" in t:
                    a = t.get("animal")
                    animals[a] = animals.get(a, 0) + 1
                    
    print(f"Day {day:02d}: Money: ${f0['money']:<7,.0f} | Animals: {animals} | Crops: {crops} | Shed: {p0_priv.get('shed', {})}")

print("Final reward:", env.steps[-1][0].reward)
