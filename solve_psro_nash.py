"""PSRO (Policy Space Response Oracles) & Meta-Nash Equilibrium Solver for Kaggriculture.
Constructs the Empirical Payoff Matrix across all Grandmaster Archetypes and solves
the exact Game-Theoretic Nash Equilibrium distribution.
"""
import copy
import json
import numpy as np
import scipy.optimize as opt
from kaggle_environments import make

from src.multi_expert_engine import MultiExpertSystem
from src.subin_an_tape import agent as subin_agent
from Archive.baseline import agent as baseline_agent
import main as elite_main


def make_oracle_agent(expert_id):
    """Wraps an expert archetype into a callable kaggle agent function."""
    engine = MultiExpertSystem()

    def agent_fn(obs):
        return engine.act(obs, macro_action=expert_id)

    return agent_fn


ORACLES = {
    0: ("VN-Orion Elite Tape", make_oracle_agent(0)),
    1: ("Subin An Moon V14", subin_agent),
    2: ("Melon IPO Blitz", make_oracle_agent(2)),
    3: ("Cow Rancher Surge", make_oracle_agent(3)),
    4: ("Fruit Continuous Engine", make_oracle_agent(4)),
    5: ("Front-Runner Interceptor", make_oracle_agent(5)),
    6: ("Apex Rule Baseline", baseline_agent),
}

BENCHMARK_TARGETS = {
    "Starter": "starter",
    "Apex Baseline": "Archive/baseline.py",
    "Main V1 Tape": "main.py",
}


def play_h2h(agent_a, agent_b, steps=720):
    """Runs a single head-to-head match and returns (score_a, score_b, margin)."""
    env = make("kaggriculture", configuration={"episodeSteps": steps}, debug=False)
    env.run([agent_a, agent_b])
    final = env.steps[-1]
    score_a = float(final[0]["observation"]["farms"][0]["money"])
    score_b = float(final[0]["observation"]["farms"][1]["money"])
    return score_a, score_b, score_a - score_b


def solve_nash_equilibrium(payoff_matrix):
    """
    Solves for the symmetric zero-sum Nash Equilibrium mixed strategy
    using Linear Programming:
        max v
        s.t. p^T M >= v
             sum(p) = 1, p >= 0
    """
    n = payoff_matrix.shape[0]
    # Invert to minimize: c = [0, 0, ..., 0, -1] for variables [p0..pn-1, v]
    c = np.zeros(n + 1)
    c[-1] = -1.0  # Maximize v

    # Constraint: -M^T p + v <= 0
    A_ub = np.zeros((n, n + 1))
    A_ub[:, :n] = -payoff_matrix.T
    A_ub[:, -1] = 1.0
    b_ub = np.zeros(n)

    # Equality: sum(p) = 1
    A_eq = np.zeros((1, n + 1))
    A_eq[0, :n] = 1.0
    b_eq = np.array([1.0])

    bounds = [(0, 1) for _ in range(n)] + [(None, None)]

    res = opt.linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.success:
        probs = res.x[:n]
        probs = np.maximum(0, probs)
        probs /= probs.sum()
        game_value = res.x[-1]
        return probs, game_value
    else:
        # Fallback to uniform if degenerate
        return np.ones(n) / n, 0.0


def run_psro_tournament():
    print("=" * 75)
    print("[*] PSRO EMPIRICAL PAYOFF MATRIX & META-NASH EQUILIBRIUM SOLVER")
    print("=" * 75)

    n_oracles = len(ORACLES)
    names = [ORACLES[i][0] for i in range(n_oracles)]

    # 1. Evaluate Benchmark Scores vs Standard Opponents
    print("\n[*] PHASE 1: EVALUATING ORACLES AGAINST STANDARD BENCHMARKS")
    print("-" * 75)
    print(f"{'ORACLE NAME':<26} | {'vs STARTER':<14} | {'vs BASELINE':<14} | {'vs MAIN V1':<14}")
    print("-" * 75)

    oracle_benchmark_scores = {}
    for i in range(n_oracles):
        name, agent_fn = ORACLES[i]
        scores = {}
        for b_name, b_target in BENCHMARK_TARGETS.items():
            _, _, margin = play_h2h(agent_fn, b_target)
            scores[b_name] = margin
        oracle_benchmark_scores[i] = scores
        print(f"{name:<26} | {scores['Starter']:>+13,.0f} | {scores['Apex Baseline']:>+13,.0f} | {scores['Main V1 Tape']:>+13,.0f}")

    # 2. Build N x N Pairwise Tournament Payoff Matrix
    print("\n" + "=" * 75)
    print("[*] PHASE 2: COMPUTING EMPIRICAL PAYOFF MATRIX (SELF-PLAY TOURNAMENT)")
    print("=" * 75)

    payoff_matrix = np.zeros((n_oracles, n_oracles))

    for i in range(n_oracles):
        for j in range(i, n_oracles):
            if i == j:
                payoff_matrix[i, j] = 0.0
            else:
                _, _, margin_ij = play_h2h(ORACLES[i][1], ORACLES[j][1])
                payoff_matrix[i, j] = margin_ij
                payoff_matrix[j, i] = -margin_ij  # Zero-sum relative margin symmetry
                print(f"Match [{names[i]}] vs [{names[j]}]: Margin = {margin_ij:>+10,.0f}")

    print("\n" + "-" * 75)
    print("EMPIRICAL PAYOFF MATRIX (Relative Cash Advantage):")
    header = " " * 26 + " | " + " | ".join([f"O{i}" for i in range(n_oracles)])
    print(header)
    print("-" * 75)
    for i in range(n_oracles):
        row_str = " | ".join([f"{payoff_matrix[i, j]/1000:>+4.0f}k" for j in range(n_oracles)])
        print(f"O{i}: {names[i]:<22} | {row_str}")

    # 3. Solve Game-Theoretic Meta-Nash Equilibrium
    print("\n" + "=" * 75)
    print("[*] PHASE 3: SOLVING EXACT META-NASH EQUILIBRIUM")
    print("=" * 75)

    nash_probs, game_value = solve_nash_equilibrium(payoff_matrix)

    print(f"\n[*] GAME VALUE AT NASH EQUILIBRIUM: {game_value:>+,.2f}")
    print("\n[*] OPTIMAL UNEXPLOITABLE STRATEGY DISTRIBUTION:")
    for i in range(n_oracles):
        pct = nash_probs[i] * 100
        bar = "#" * int(pct / 3)
        print(f"  * O{i}: {names[i]:<26} -> {pct:>5.1f}%  {bar}")

    # Save PSRO Meta-Nash Policy Configuration
    config = {
        "oracles": {str(i): names[i] for i in range(n_oracles)},
        "nash_weights": {str(i): float(nash_probs[i]) for i in range(n_oracles)},
        "payoff_matrix": payoff_matrix.tolist(),
        "benchmark_scores": {str(i): oracle_benchmark_scores[i] for i in range(n_oracles)}
    }
    with open("psro_nash_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\n[+] Saved PSRO Game Theory Configuration to: psro_nash_config.json")
    print("=" * 75)



if __name__ == "__main__":
    run_psro_tournament()
