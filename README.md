# Twenty Bits

![Every scheduled main endpoint on matched frozen games](results/main_B41/charts/all-endpoints.png)

![Offline random versus greedy predicate replay with noisy answers](replays/baseline-noisy.gif)

**Better questions, different ways to lose.** Outcome-only RL raises noiseless animal EIG/question from raw base **0.158** to **0.634 (A11)**, **0.390 (A23)** and **0.437 (B41)**. Their animal wins are **24/56, 25/56 and 19/56**, versus base **7/56**. A11 and B41 gamble; A23 stalls. Across the full bank, A11 makes 167 wrong guesses, A23 leaves 136 games without guessing, and B41 makes 152 wrong guesses. These are fitted endpoints, not stable estimates of every training seed.

The noisy-trained B41 wins **36/140** noisy games, versus A11's 31, A23's 29 and raw base's 52. Relative to mean A, B41's win-rate change is **+0.043 [95% CI -0.018, +0.107]** and noisy EIG change is **+0.031 [0.001, 0.053]**. These paired game/A-seed intervals condition on the only B endpoint. They do not establish a general noise-training or re-checking benefit.

Noiseless synthetic transfer wins are **raw 82/84, A11 49/84, A23 84/84, B41 72/84**. Raw base already searches these random tables well. A11's severe identifier-copying regression does not replicate in A23; B41 has fewer, mixed copying/syntax errors. Legal item-name enumeration is absent, while malformed name-query attempts remain logged and penalized. High EIG alone does not guarantee enough evidence before guessing.

The task supplies remaining candidates after each answer and measures question selection given that state. Reward is **+1 win, -0.03/question, -0.1/INVALID**; EIG is measured, never rewarded. All three policies start from provider Qwen3-8B without project SFT. The prompt states the fixed question maximum but no dynamic remaining count: all 110 A23 post-budget ASK inputs had the maximum in history, and none had a per-turn remaining count or exhaustion notice. [Exact prompt audit](research/BUDGET_VISIBILITY.md).

[MAIN_B41_GATE.md](MAIN_B41_GATE.md) contains every B41 update/check, all three seeds' cell tables, guess-with-k, early guesses, paired CIs, re-check denominators, the invalid name-reference audit and [two preselected paired examples](results/main_B41/EXAMPLE_GAMES.md). [A23](MAIN_A23_GATE.md), [A11](MAIN_A11_GATE.md) and earlier failed configurations remain historical. Hard mode ran on raw base/A23 only (0/20 each); B41 adds its scheduled primary endpoint.

**Recorded project usage: $20.100658 / $50.00; held $2.083181; available $27.816161**, from [ledger.json](ledger.json). Invoice reconciliation is pending. B41 used **$3.974884 plus $0.443049 held**, within its **$13.64 forecast including margin**. Both native endpoint types have no expiry. The live ledger now uses durable SQLite transactions; migration preserved every old entry and hold. The B41 run finished at 16-game concurrency without a lost request or replacement. [Budget](BUDGET.md), [ledger storage and performance](LEDGER.md).

**Stopped at the B41 gate. No further paid work is authorized.** The final RESULTS.md and model replay exports remain the next offline phase. The GIF above is a baseline illustration, not a trained-model replay.

Open the [interactive baseline replay](replays/index.html), [truthful-answer MP4](replays/baseline-noiseless.mp4), or [noisy-answer MP4](replays/baseline-noisy.mp4). The two illustrated games were selected for visible strategy contrast; complete sweeps supply the reported baseline numbers.

The offline grid contains 24,000 games, with 200 paired games for each domain, candidate size, noise setting, and policy. [Every cell](results/baselines/BASELINES.md), [machine-readable metrics and 95% bootstrap CIs](results/baselines/summary.json), and [matched frozen-game references](results/baselines/frozen/summary.json) are saved. Greedy predicate's macro-average EIG is 0.9976 bits/question with truthful answers and 0.4994 with 10% noise. Its observed win rates are 100% and 81.925%. The noisy answer-channel ceiling is 0.5310 bits/question.

These are finite authored worlds. Animals has 400 named age/sex profiles across 100 types; tools and foods each have 320 profiles across 80 types. They use 90, 88, and 71 attributes to stay distinguishable without random identity bits. The synthetic world has 512 unique random 16-bit rows and is relabeled in each game. [World definitions, sample hand checks, and limitations](data/WORLDS.md) describe the construction. Animal training uses a fixed 200-row pool; paid animal evaluation uses disjoint rows, with shared underlying types disclosed.

[PAID_PLANS.md](PAID_PLANS.md) records the approved $50 cap and selected U plan. [MAIN_B41_GATE.md](MAIN_B41_GATE.md) is the current stop; [PAUSED.md](PAUSED.md) preserves the earlier pause and resume point. [PRIOR_WORK.md](PRIOR_WORK.md) stays as context; this is a side project for GitHub and X.

## Reproduce offline

Use Python 3.11 or later. The game and core tests do not need Tinker credentials or its SDK. Paid-adapter tests require the paid extra and use mocked requests.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[replay]'
python3 -m unittest discover -s tests -v
python3 scripts/verify_frozen.py
python3 scripts/run_baselines.py
python3 scripts/run_frozen_baselines.py
python3 scripts/plot_baselines.py
python3 scripts/measure_tokens.py
python3 scripts/build_paid_plans.py
python3 scripts/status_B41.py --snapshot
```

Tokenizer downloads come from Hugging Face at the recorded revisions. No weights are downloaded. The baseline runners reuse the committed per-game results when present and verify their world, tokenizer, and seed provenance. To compute another sweep independently, use `python3 scripts/run_baselines.py --output-directory /tmp/twenty-bits-reproduction`. The frozen bank is already included; `freeze_evals.py` refuses to overwrite it.

Serve the viewer with `python3 -m http.server 8765` and visit `http://localhost:8765/replays/`. Play, scrub, step, change noise mode, hide the target, or load a matched pair in the JSON schema from replays/games.json. Regenerate the local exports with `python3 scripts/export_replays.py`. This uses the pinned HyperFrames CLI and FFmpeg. To rebuild only GIFs from existing MP4s, add `--reuse-mp4`.

## Reproduce the current paid analysis offline

```bash
python3 -m pip install -e '.[paid,replay]'
python3 scripts/analyze_main_B41.py
python3 scripts/analyze_all_main_seeds.py
python3 scripts/verify_main_B41.py
python3 scripts/plot_main_B41.py
python3 scripts/plot_all_main_seeds.py
python3 scripts/write_main_B41_gate.py
python3 scripts/status_B41.py --snapshot
```

These commands read committed compressed traces, finished-session metadata and the completed ledger JSON export. They make no service calls and do not need credentials, raw run caches, adapter weights or the live SQLite database. [Reproduction proof](results/main_B41/reproduction.json) includes archive hashes; the check also runs in a separate Git-only checkout. Tokenizers use pinned cached files or download those files from Hugging Face. Unit tests mock service operations.

The live database is ignored and missing live state fails closed. `--snapshot` explicitly reads the completed export; it may be stale during an active run. Do not reconstruct an active ledger from an old export to resume spending. The append-only change history is [archived and checked](research/ledger_events_archive.json).

Historical gate checks belong at their corresponding commits because ledger totals and source hashes have changed. Do not rebuild A11/A23 summaries against today's ledger. Completed paid runners return before service access. `.env`, raw run caches and adapter binaries remain ignored and untracked.

## Read the code

[LEARN.md](LEARN.md) explains each completed phase. Start with [worlds.py](twenty_bits/worlds.py), [predicates.py](twenty_bits/predicates.py), [information.py](twenty_bits/information.py), and [game.py](twenty_bits/game.py), then read [baselines.py](twenty_bits/baselines.py). The public observation is built in [prompts.py](twenty_bits/prompts.py), and frozen-game checks live in [evaluation.py](twenty_bits/evaluation.py).

[PROTOCOL.md](PROTOCOL.md) fixes the grammar, budget, posterior, metrics, and stopping rules. [NUMBERS.md](NUMBERS.md) records the main comparisons. EIG is measured and never rewarded. Legal name enumeration remains allowed, and the approved output cap accommodates the measured half-candidate lists. The final RESULTS.md will tie model claims to charts, paired CIs, spend, and failed attempts after those data exist.

The paid bridge lives in [model_player.py](twenty_bits/model_player.py), [tinker_rendering.py](twenty_bits/tinker_rendering.py), and [tinker_transport.py](twenty_bits/tinker_transport.py). [candidate_feedback.py](twenty_bits/candidate_feedback.py) supplies the versioned main observation without changing historical prompts. [The candidate-set reproduction check](results/candidate_set/reproduction.json) verifies saved-archive analysis. The transport persists IDs before sampling, reserves the full declared cost, and handles pending retrieval without repeating sampling.

[rl_pilot.py](twenty_bits/rl_pilot.py) builds group-standardized advantages and guarded SDK training operations. [run_rl_pilot.py](scripts/run_rl_pilot.py) joins cookbook rollouts, training and scheduled development checks. [analyze_rl_pilot.py](scripts/analyze_rl_pilot.py) replays actions, verifies exact rewards and training masks, and builds the audit. The pilot starts from raw base and never loads the historical SFT adapter.

[run_main_seed.py](scripts/run_main_seed.py) adds the full matched control, the 30-update curriculum and mandatory A11 gate. [guess_metrics.py](twenty_bits/guess_metrics.py) measures stopping with k candidates; it changes no reward or observation. [recovery.py](twenty_bits/recovery.py) enforces one exact replacement per lost logical sample, retained original holds and permanent output exclusion. [analyze_main_seed.py](scripts/analyze_main_seed.py) replays the run and audits transfer identifiers; [verify_main_seed.py](scripts/verify_main_seed.py) verifies the archived analysis and completed-run guard. The historical pause verifier belongs at its pause commit.

[run_main_A23.py](scripts/run_main_A23.py) preserves the second A seed's schedule and native permanent endpoint saves. [run_A23_endpoint_aux.py](scripts/run_A23_endpoint_aux.py) keeps the suffix diagnostic and hard mode separate. [analyze_main_A23.py](scripts/analyze_main_A23.py), [analyze_A23_replication.py](scripts/analyze_A23_replication.py) and [verify_main_A23.py](scripts/verify_main_A23.py) replay accepted outputs, reconstruct all gradient batches and reproduce comparisons from committed archives. [name_reference_audit.py](twenty_bits/name_reference_audit.py) detects malformed name queries without accepting or rewarding them.

[run_main_B41.py](scripts/run_main_B41.py) preserves the declared noisy training condition and scheduled endpoint. [analyze_all_main_seeds.py](scripts/analyze_all_main_seeds.py) reports every cell and distinguishes paired-game uncertainty from the missing B seed variability. [ledger_store.py](twenty_bits/ledger_store.py) stores durable indexed reservations and append-only change records; the financial transitions remain in [budget.py](twenty_bits/budget.py).
