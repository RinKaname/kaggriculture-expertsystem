import time
import argparse
import statistics
import math
from kaggle_environments import make

# Import agents
from main import agent as my_agent

# Import opponents
EXTRA_OPPONENTS = {}
try:
    import Archive.baseline as baseline1
    EXTRA_OPPONENTS["baseline"] = baseline1.agent
    EXTRA_OPPONENTS["baseline1"] = baseline1.agent
except Exception:
    pass

try:
    import Archive.baseline2 as baseline2
    EXTRA_OPPONENTS["baseline2"] = baseline2.agent
except Exception:
    pass

try:
    import replica
    EXTRA_OPPONENTS["replica"] = replica.agent
    EXTRA_OPPONENTS["top_bot"] = replica.agent
except Exception:
    pass


def print_ascii_histogram(data, bins=5, title="Score Distribution"):
    if not data or len(data) < 2:
        return
    min_val, max_val = min(data), max(data)
    if min_val == max_val:
        print(f"  All scores identical: ${min_val:,.0f}")
        return

    bin_width = (max_val - min_val) / bins
    counts = [0] * bins
    for val in data:
        idx = int((val - min_val) / bin_width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    max_count = max(counts) if max(counts) > 0 else 1
    max_bar_len = 25

    print(f"\n  [+] {title} (Histogram):")
    for i in range(bins):
        low = min_val + i * bin_width
        high = low + bin_width
        bar_len = int((counts[i] / max_count) * max_bar_len)
        bar = "#" * bar_len + "-" * (max_bar_len - bar_len)
        print(f"  ${low:>8,.0f} - ${high:>8,.0f} | [{bar}] ({counts[i]:>2d} games)")


def calculate_eda(scores):
    if not scores:
        return {}
    n = len(scores)
    sorted_s = sorted(scores)
    mean_val = statistics.mean(scores)
    stdev_val = statistics.stdev(scores) if n > 1 else 0.0
    min_val = min(scores)
    max_val = max(scores)
    median_val = statistics.median(scores)

    def get_percentile(p):
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_s[int(k)]
        d0 = sorted_s[int(f)] * (c - k)
        d1 = sorted_s[int(c)] * (k - f)
        return d0 + d1

    q1 = get_percentile(0.25)
    q3 = get_percentile(0.75)
    iqr = q3 - q1
    p10 = get_percentile(0.10)
    p90 = get_percentile(0.90)

    return {
        "n": n,
        "mean": mean_val,
        "std": stdev_val,
        "min": min_val,
        "p10": p10,
        "q1": q1,
        "median": median_val,
        "q3": q3,
        "p90": p90,
        "max": max_val,
        "iqr": iqr
    }


def run_benchmark(num_games=10, opponent="starter", debug=False):
    # Resolve opponent
    opp_agent = EXTRA_OPPONENTS.get(opponent.lower(), opponent)
    
    print("=" * 68)
    print(f"KAGGRICULTURE BENCHMARK & EDA: 'main.py' vs '{opponent}' ({num_games} games)")
    print("=" * 68)
    
    my_scores = []
    opp_scores = []
    margins = []
    
    p0_my_scores = []
    p0_opp_scores = []
    p1_my_scores = []
    p1_opp_scores = []
    
    wins = 0
    draws = 0
    losses = 0
    p0_wins = 0
    p1_wins = 0
    total_time = 0.0
    times = []

    for game_idx in range(num_games):
        t0 = time.time()
        as_player_0 = (game_idx % 2 == 0)
        agents = [my_agent, opp_agent] if as_player_0 else [opp_agent, my_agent]
        
        env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=debug)
        env.run(agents)
        elapsed = time.time() - t0
        total_time += elapsed
        times.append(elapsed)

        final_step = env.steps[-1]
        p0_reward = float(final_step[0].reward)
        p1_reward = float(final_step[1].reward)

        my_reward = p0_reward if as_player_0 else p1_reward
        opp_reward = p1_reward if as_player_0 else p0_reward
        margin = my_reward - opp_reward

        my_scores.append(my_reward)
        opp_scores.append(opp_reward)
        margins.append(margin)

        if as_player_0:
            p0_my_scores.append(my_reward)
            p0_opp_scores.append(opp_reward)
        else:
            p1_my_scores.append(my_reward)
            p1_opp_scores.append(opp_reward)

        if my_reward > opp_reward:
            wins += 1
            if as_player_0: p0_wins += 1
            else: p1_wins += 1
            result = "WIN "
        elif my_reward == opp_reward:
            draws += 1
            result = "DRAW"
        else:
            losses += 1
            result = "LOSS"

        pos_str = "P0 (First)" if as_player_0 else "P1 (Second)"
        margin_sign = "+" if margin > 0 else ""
        print(f"Game {game_idx + 1:02d}/{num_games:02d} [{pos_str:<10}]: {result} | My: ${my_reward:>8,.0f} | Opp: ${opp_reward:>8,.0f} | Margin: {margin_sign}${margin:>8,.0f} | {elapsed:.2f}s")

    win_rate = (wins / num_games) * 100.0
    eda_my = calculate_eda(my_scores)
    eda_opp = calculate_eda(opp_scores)
    eda_margin = calculate_eda(margins)

    # Print Full EDA Summary
    print("\n" + "=" * 68)
    print("EXPLORATORY DATA ANALYSIS (EDA) & BENCHMARK REPORT")
    print("=" * 68)
    print(f"Overall Record: {wins} Wins / {draws} Draws / {losses} Losses | Win Rate: {win_rate:.1f}%")
    print(f"Total Time:     {total_time:.2f}s (Avg {statistics.mean(times):.2f}s/game, Min {min(times):.2f}s, Max {max(times):.2f}s)")
    print("-" * 68)

    print(f"{'METRIC':<20} | {'MY SCORE (Agent)':<22} | {'OPPONENT SCORE':<20}")
    print("-" * 68)
    print(f"{'Mean (Average)':<20} | ${eda_my['mean']:>18,.2f}  | ${eda_opp['mean']:>16,.2f}")
    print(f"{'Std Dev (s)':<20} | ${eda_my['std']:>18,.2f}  | ${eda_opp['std']:>16,.2f}")
    print(f"{'Lowest (Min)':<20} | ${eda_my['min']:>18,.2f}  | ${eda_opp['min']:>16,.2f}")
    print(f"{'10th Percentile (P10)':<20} | ${eda_my['p10']:>18,.2f}  | ${eda_opp['p10']:>16,.2f}")
    print(f"{'25th Percentile (Q1)':<20} | ${eda_my['q1']:>18,.2f}  | ${eda_opp['q1']:>16,.2f}")
    print(f"{'Median (50th)':<20} | ${eda_my['median']:>18,.2f}  | ${eda_opp['median']:>16,.2f}")
    print(f"{'75th Percentile (Q3)':<20} | ${eda_my['q3']:>18,.2f}  | ${eda_opp['q3']:>16,.2f}")
    print(f"{'90th Percentile (P90)':<20} | ${eda_my['p90']:>18,.2f}  | ${eda_opp['p90']:>16,.2f}")
    print(f"{'Highest (Max)':<20} | ${eda_my['max']:>18,.2f}  | ${eda_opp['max']:>16,.2f}")
    print(f"{'Interquartile (IQR)':<20} | ${eda_my['iqr']:>18,.2f}  | ${eda_opp['iqr']:>16,.2f}")
    print("-" * 68)

    # Position Asymmetry EDA (P0 vs P1)
    if p0_my_scores and p1_my_scores:
        p0_wr = (p0_wins / len(p0_my_scores)) * 100.0
        p1_wr = (p1_wins / len(p1_my_scores)) * 100.0
        print("\n[+] POSITION BIAS & ASYMMETRY ANALYSIS:")
        print(f"  - As Player 0 (P0): Win Rate {p0_wr:>5.1f}% ({p0_wins}/{len(p0_my_scores)}) | Avg: ${statistics.mean(p0_my_scores):>8,.0f} | Min: ${min(p0_my_scores):>8,.0f} | Max: ${max(p0_my_scores):>8,.0f}")
        print(f"  - As Player 1 (P1): Win Rate {p1_wr:>5.1f}% ({p1_wins}/{len(p1_my_scores)}) | Avg: ${statistics.mean(p1_my_scores):>8,.0f} | Min: ${min(p1_my_scores):>8,.0f} | Max: ${max(p1_my_scores):>8,.0f}")
        p_delta = statistics.mean(p0_my_scores) - statistics.mean(p1_my_scores)
        sign = "+" if p_delta > 0 else ""
        print(f"  - First Mover Delta (P0 - P1): {sign}${p_delta:,.2f}")

    # Margin of Victory Summary
    print("\n[+] VICTORY MARGIN ANALYSIS (My Score - Opp Score):")
    print(f"  - Mean Margin:   ${eda_margin['mean']:>10,.2f}")
    print(f"  - Median Margin: ${eda_margin['median']:>10,.2f}")
    print(f"  - Min Margin:    ${eda_margin['min']:>10,.2f}")
    print(f"  - Max Margin:    ${eda_margin['max']:>10,.2f}")

    # Visual ASCII Histogram
    print_ascii_histogram(my_scores, bins=min(6, max(3, num_games // 2)), title="My Agent Score Distribution")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kaggriculture Benchmark & Statistical EDA Runner")
    parser.add_argument("--games", type=int, default=10, help="Number of games to simulate")
    parser.add_argument("--opponent", type=str, default="starter", help="Opponent agent (starter, random, pass, baseline, baseline2)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    run_benchmark(num_games=args.games, opponent=args.opponent, debug=args.debug)
