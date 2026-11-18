# Twenty Bits

![Base model and matched information-seeking baselines](results/phase2/charts/base-v-baselines.png)

![Random versus greedy predicate, with noisy answers](replays/baseline-noisy.gif)

Can an outcome-only reward teach a small LLM to search efficiently, and does it learn attribute bisection or item-name enumeration? Does the strategy transfer to relabeled tables, and does noise teach it to re-check answers?

**Format SFT is complete; no RL has run. Recorded Tinker usage: $6.315686 / $50.00, with $0.112813 held**, from [ledger.json](ledger.json). Exact attribute-code aliases raised pooled valid turns to 72.6%. The approved conditional SFT then reached 92.0% valid turns on qualification, but won only 3/32 games against the required 8/32. Work stops before RL. [The current gate](ALIAS_GATE.md) has the grammar rules, every cell, CIs, costs, and guess-consistency failures. Invoice reconciliation remains pending.

The chart compares the original base model with matched baselines; the GIF illustrates random versus greedy search. [Phase 2 metrics, CIs, tokens, and cost](PHASE2.md) preserve the historical names-only evaluation. [The diagnosis](DIAGNOSIS.md) includes three full transcripts. New qualification uses smaller development games and is not a paired estimate of SFT's effect. The gpt-oss-120b reference is removed from future plans because its configured cap mostly produced analysis without actions.

Open the [interactive replay](replays/index.html), [truthful-answer MP4](replays/baseline-noiseless.mp4), or [noisy-answer MP4](replays/baseline-noisy.mp4). The two illustrated games were selected for a visible strategy contrast. The complete sweeps supply the reported numbers.

The offline grid contains 24,000 games, with 200 paired games for each domain, candidate size, noise setting, and policy. [Every cell](results/baselines/BASELINES.md), [machine-readable metrics and 95% bootstrap CIs](results/baselines/summary.json), and [matched frozen-game references](results/baselines/frozen/summary.json) are saved. Greedy predicate's macro-average EIG is 0.9976 bits/question with truthful answers and 0.4994 with 10% noise. Its observed win rates are 100% and 81.925%. The noisy answer-channel ceiling is 0.5310 bits/question.

These are finite authored worlds. Animals has 400 named age/sex profiles across 100 types; tools and foods each have 320 profiles across 80 types. They use 90, 88, and 71 attributes to stay distinguishable without random identity bits. The synthetic world has 512 unique random 16-bit rows and is relabeled in each game. [World definitions, sample hand checks, and limitations](data/WORLDS.md) describe the construction. Animal training uses a fixed 200-row pool; paid animal evaluation uses disjoint rows, with shared underlying types disclosed.

[PAID_PLANS.md](PAID_PLANS.md) records the approved $50 budget and groups of eight. [ALIAS_GATE.md](ALIAS_GATE.md) is the current gate report. Work is stopped after failed qualification. Main options S and U will be priced after a pilot is approved and its learning speed is measured. [PRIOR_WORK.md](PRIOR_WORK.md) stays as context; this is a side project for GitHub and X.

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
python3 -m twenty_bits.budget status
```

Tokenizer downloads come from Hugging Face at the recorded revisions. No weights are downloaded. The baseline runners reuse the committed per-game results when present and verify their world, tokenizer, and seed provenance. To compute another sweep independently, use `python3 scripts/run_baselines.py --output-directory /tmp/twenty-bits-reproduction`. The frozen bank is already included; `freeze_evals.py` refuses to overwrite it.

Serve the viewer with `python3 -m http.server 8765` and visit `http://localhost:8765/replays/`. Play, scrub, step, change noise mode, hide the target, or load a matched pair in the JSON schema from replays/games.json. Regenerate the local exports with `python3 scripts/export_replays.py`. This uses the pinned HyperFrames CLI and FFmpeg. To rebuild only GIFs from existing MP4s, add `--reuse-mp4`.

## Reproduce the paid analysis offline

```bash
python3 -m pip install -e '.[paid]'
python3 scripts/verify_rendering.py
python3 scripts/summarize_phase2.py
python3 scripts/verify_phase2.py
python3 scripts/plot_phase2.py
python3 scripts/diagnose_phase2.py
python3 scripts/measure_random_learnability.py
python3 scripts/price_format_warmstart.py
python3 scripts/summarize_learnability_probe.py
python3 scripts/reprice_learnability.py
python3 scripts/write_learnability_report.py
python3 scripts/break_down_zero_eig.py
python3 scripts/summarize_alias_probe.py
python3 scripts/summarize_format_sft.py
python3 scripts/audit_qualification.py
python3 scripts/write_alias_gate.py
```

These commands use saved traces and request metadata, without service calls or credentials. The tokenizers use pinned local files or download those files from Hugging Face. `build_paid_plans.py` rebuilds the historical Phase 1 proposals; `build_approved_plan.py` reprices the approved group-size changes. The [Phase 2 reproduction check](results/phase2/reproduction.json) and [SFT qualification reproduction check](results/format_sft/reproduction.json) confirm analysis is identical without local run caches. Completed runners and saved request IDs prevent resubmission. RL still needs the next gate approval. `.env` is ignored and untracked.

## Read the code

[LEARN.md](LEARN.md) explains each completed phase. Start with [worlds.py](twenty_bits/worlds.py), [predicates.py](twenty_bits/predicates.py), [information.py](twenty_bits/information.py), and [game.py](twenty_bits/game.py), then read [baselines.py](twenty_bits/baselines.py). The public observation is built in [prompts.py](twenty_bits/prompts.py), and frozen-game checks live in [evaluation.py](twenty_bits/evaluation.py).

[PROTOCOL.md](PROTOCOL.md) fixes the grammar, budget, posterior, metrics, and stopping rules. [NUMBERS.md](NUMBERS.md) records the main comparisons. EIG is measured and never rewarded. Legal name enumeration remains allowed, and the approved output cap accommodates the measured half-candidate lists. The final RESULTS.md will tie model claims to charts, paired CIs, spend, and failed attempts after those data exist.

The paid bridge lives in [model_player.py](twenty_bits/model_player.py), [tinker_rendering.py](twenty_bits/tinker_rendering.py), and [tinker_transport.py](twenty_bits/tinker_transport.py). The transport persists IDs before sampling, reserves the full declared cost, and handles pending retrieval without repeating sampling.
