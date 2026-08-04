
==================== [Cell 0] ====================
<div style="padding:30px 32px;border-radius:24px;background:linear-gradient(125deg,#102a43,#0f766e 52%,#f59e0b);color:white;box-shadow:0 16px 40px rgba(15,118,110,.25)">
  <div style="font-size:14px;letter-spacing:.16em;text-transform:uppercase;opacity:.86">Kaggriculture • Public Replay Distillation • Executed Submission</div>
  <h1 style="margin:.35em 0 .18em;font-size:43px;line-height:1.06">The 720-Turn Farm Tape</h1>
  <p style="font-size:19px;max-width:940px;margin:0;opacity:.96">Version 12 turns one publicly downloadable top-player replay into a tiny, no-I/O policy—then stress-tests it across seeds, opponents, and both seats.</p>
</div>

## What this notebook contributes

- the exact, standalone `main.py` and `submission.tar.gz`;
- a visual teardown of the farm's capital curve, crop rotation, herd, labor, geometry, and market actions;
- a broad untouched-seed cross-play gate against public and campaign controls;
- a direct falsification of the tempting **all-melons** strategy;
- an unusually simple starter: return the action scheduled for `obs.step`.

**Provenance first.** The action sequence was distilled from public episode **89256171**, played by [radiant-allomancer](https://www.kaggle.com/radiantallomancer) against **nishchal jain**. The public replay scored **130,895 vs 117,910**. This notebook does **not** claim the player's private source or strategy authorship. Kaggle's [competition rules](https://www.kaggle.com/competitions/kaggriculture/rules) state that replays, including actions, may be made publicly available and downloadable.

> Cross-play below is local evidence from the official simulator. It is not a public leaderboard score; only a completed Kaggle submission can establish that.

==================== [Cell 2] ====================
## 1. Why a fixed tape can work

Kaggriculture has stochastic weeds and shared prices, but the board geometry, 30-day clock, action cadence, and core growth rules are stable. A high-quality tape can therefore encode an entire capital schedule: buy productive assets early, unlock land on time, keep labor ahead of the job queue, and liquidate before the final bell. Invalid or unavailable commands degrade harmlessly while the rest of the day's parallel commands still execute.

The strength is also the limitation: the tape observes only `step`. It does not adapt to a rival's farm or recover intelligently from a major state divergence. Treat it as a high-scoring launchpad and a compressed behavioral dataset—not as the final form of an adaptive agent.

==================== [Cell 5] ====================
## 2. Mathematical control: all melons is an opening, not a strategy

A watered melon tile can produce six premium units, but the sale curve is quadratic in glut. Dumping a whole monoculture into the same market makes each later tile sharply less valuable. The replay uses a small early melon tranche for explosive capital, then rotates into strawberries while livestock adds diversified milk, wool, and fertilizer value.

==================== [Cell 7] ====================
## 3. Teardown of public episode 89256171

These plots are descriptive measurements of the public replay—not evidence about hidden implementation. The farm front-loads four animals and six melon seeds in the first market turn, uses 4 hands on day 0, expands to a 16-animal mixed herd, then sustains roughly a dozen hands while the crop book rotates toward strawberries.

==================== [Cell 14] ====================
## 4. Untouched-seed promotion gate

The candidate below was frozen before this larger matrix. Each pairing uses complete 720-turn games from both player positions. Opponents include strong public notebooks, prior versions, fixed portfolio counters, and freshly downloaded public agents. The heatmaps expose failures instead of hiding them behind one aggregate.

==================== [Cell 16] ====================
## 5. Write the distilled agent

The policy below is deliberately inspectable: one action dictionary for each observation step, selected with a bounds-safe index and deep-copied before return. It has no internet, replay-file, dataset, model, or notebook-global dependency at inference time.

**Attribution:** the behavioral tape is derived from the publicly downloadable action sequence of [radiant-allomancer](https://www.kaggle.com/radiantallomancer) in episode **89256171**. The packaging, robustness tests, visual analysis, and presentation here are this notebook's contribution. Do not describe the underlying behavior as independently authored source code.

==================== [Cell 18] ====================
### Live execution proof

This is not a mock: the cell reloads the written file and runs complete official-simulator episodes from both positions. The notebook fails if either side does not reach `DONE`.

==================== [Cell 21] ====================
## 6. Package integrity

The competition archive contains exactly one root file, `main.py`. Use this notebook version's **Submit to competition** button and choose `submission.tar.gz`.

==================== [Cell 23] ====================
---

## Turn this starter into an adaptive frontier

1. **Behavior-clone by state, not step.** Use public replay observations and actions as supervised examples, then retrieve or predict actions from the current farm state.
2. **Add legality-aware repair.** When a taped action misses, redirect the freed hand to the highest-value nearby care, feed, harvest, water, or drop job.
3. **Condition the market block.** Preserve the tape's capital schedule but size buys and sells from live inventory, price, town demand, and rival exposure.
4. **Ensemble tapes.** Select a schedule by early weed pressure or opponent acreage instead of committing to one episode at step 0.
5. **Keep symmetric gates.** Shared-market ordering makes player position real; every promotion should use both seats and untouched seeds.

The key result is less mystical than it looks: a great Kaggriculture farm is a timed supply chain. This notebook makes one elite public trajectory executable, measurable, and easy to improve. If it saves you days of reverse engineering, an upvote helps other competitors find the evidence and the caveats. 🌾
