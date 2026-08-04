import time
from kaggle_environments import make
import main
import Archive.baseline as baseline

def run_h2h(games=4):
    print(f"=== Running Head-to-Head: main.py vs Archive/baseline.py ({games} games) ===")
    main_scores = []
    base_scores = []
    wins = 0
    draws = 0
    losses = 0

    for g in range(games):
        t0 = time.time()
        as_p0 = (g % 2 == 0)
        agents = [main.agent, baseline.agent] if as_p0 else [baseline.agent, main.agent]
        
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
        env.run(agents)
        elapsed = time.time() - t0

        p0_score = float(env.steps[-1][0].reward or 0)
        p1_score = float(env.steps[-1][1].reward or 0)

        m_score = p0_score if as_p0 else p1_score
        b_score = p1_score if as_p0 else p0_score

        main_scores.append(m_score)
        base_scores.append(b_score)

        if m_score > b_score:
            wins += 1
            res = "WIN"
        elif m_score == b_score:
            draws += 1
            res = "DRAW"
        else:
            losses += 1
            res = "LOSS"

        print(f"Game {g+1:02d}/{games:02d} (main as P{0 if as_p0 else 1}): {res} | main.py: ${m_score:,.0f} vs baseline: ${b_score:,.0f} | Time: {elapsed:.2f}s")

    print("\n" + "=" * 50)
    print("HEAD-TO-HEAD SUMMARY:")
    print(f"  main.py Win Rate:  {wins / games * 100:.1f}% ({wins}W / {draws}D / {losses}L)")
    print(f"  Avg main.py Score: ${sum(main_scores) / len(main_scores):,.2f}")
    print(f"  Avg baseline Score: ${sum(base_scores) / len(base_scores):,.2f}")
    print("=" * 50)

if __name__ == "__main__":
    run_h2h(games=4)
