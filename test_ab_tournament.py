import time
from kaggle_environments import make
import main
import Archive.baseline as baseline1
import Archive.baseline2 as baseline2

def run_match(agent_a, agent_b, name_a, name_b, num_games=4):
    print(f"\n==================================================")
    print(f" MATCH: {name_a} vs {name_b} ({num_games} Games)")
    print(f"==================================================")
    
    wins_a = 0
    wins_b = 0
    draws = 0
    scores_a = []
    scores_b = []

    for game_idx in range(num_games):
        as_p0 = (game_idx % 2 == 0)
        agents = [agent_a, agent_b] if as_p0 else [agent_b, agent_a]
        
        t0 = time.time()
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        env.run(agents)
        dt = time.time() - t0

        r0 = env.steps[-1][0]["reward"] or 0
        r1 = env.steps[-1][1]["reward"] or 0

        score_a = r0 if as_p0 else r1
        score_b = r1 if as_p0 else r0
        
        scores_a.append(score_a)
        scores_b.append(score_b)

        if score_a > score_b:
            res = f"{name_a} WIN"
            wins_a += 1
        elif score_b > score_a:
            res = f"{name_b} WIN"
            wins_b += 1
        else:
            res = "DRAW"
            draws += 1

        pos_str = f"P0" if as_p0 else f"P1"
        print(f"Game {game_idx+1:02d}/{num_games:02d} ({name_a} as {pos_str}): {res:<12} | {name_a}: ${score_a:,.0f} vs {name_b}: ${score_b:,.0f} | Time: {dt:.2f}s")

    avg_a = sum(scores_a) / len(scores_a)
    avg_b = sum(scores_b) / len(scores_b)
    win_rate = (wins_a / num_games) * 100

    print(f"--------------------------------------------------")
    print(f"SUMMARY: {name_a} vs {name_b}")
    print(f"  {name_a} Win Rate: {win_rate:.1f}% ({wins_a}W / {draws}D / {wins_b}L)")
    print(f"  Avg {name_a} Score: ${avg_a:,.2f}")
    print(f"  Avg {name_b} Score: ${avg_b:,.2f}")
    print(f"--------------------------------------------------")
    return avg_a, avg_b, win_rate

if __name__ == "__main__":
    print("STARTING TOURNAMENT BENCHMARK FOR A/B TESTING...")
    
    # 1. Main vs Baseline 1
    run_match(main.agent, baseline1.agent, "main.py (Blitz)", "baseline.py (V1)", num_games=4)

    # 2. Main vs Baseline 2
    run_match(main.agent, baseline2.agent, "main.py (Blitz)", "baseline2.py (V2)", num_games=4)
