# Twenty Bits

![Base model and matched information-seeking baselines](results/phase2/charts/base-v-baselines.png)

![Random versus greedy predicate, with noisy answers](replays/baseline-noisy.gif)

Can an outcome-only reward teach a small LLM to search efficiently, and does it learn attribute bisection or item-name enumeration? Does the strategy transfer to relabeled tables, and does noise teach it to re-check answers?

**No SFT or RL training has run. Recorded Tinker token-usage cost: $5.862788 / $50.00, with $0.012813 held**, from [ledger.json](ledger.json). Phase 2 Qwen3-8B won 0/280 games; the 512-token gpt-oss-120b reference won 0/20. A later prompt-only development probe won 1/16 at N=8 and 0/16 at N=16, with low valid-turn rates. [The diagnosis](DIAGNOSIS.md) explains the failures and cost, with three complete transcripts. [The learnability gate](LEARNABILITY.md) prices a grammar warm start and guarded pilot. Both need approval. Invoice reconciliation remains pending.

The chart compares the original base model with matched baselines; the GIF illustrates random versus greedy search. [Phase 2 metrics, CIs, tokens, and cost](PHASE2.md) preserve the historical evaluation. The development probe uses a different prompt and smaller sizes, so its change is not an isolated prompt effect.

Open the [interactive replay](replays/index.html), [truthful-answer MP4](replays/baseline-noiseless.mp4), or [noisy-answer MP4](replays/baseline-noisy.mp4). The two illustrated games were selected for a visible strategy contrast. The complete sweeps supply the reported numbers.

The offline grid contains 24,000 games, with 200 paired games for each domain, candidate size, noise setting, and policy. [Every cell](results/baselines/BASELINES.md), [machine-readable metrics and 95% bootstrap CIs](results/baselines/summary.json), and [matched frozen-game references](results/baselines/frozen/summary.json) are saved. Greedy predicate's macro-average EIG is 0.9976 bits/question with truthful answers and 0.4994 with 10% noise. Its observed win rates are 100% and 81.925%. The noisy answer-channel ceiling is 0.5310 bits/question.

These are finite authored worlds. Animals has 400 named age/sex profiles across 100 types; tools and foods each have 320 profiles across 80 types. They use 90, 88, and 71 attributes to stay distinguishable without random identity bits. The synthetic world has 512 unique random 16-bit rows and is relabeled in each game. [World definitions, sample hand checks, and limitations](data/WORLDS.md) describe the construction. Animal training uses a fixed 200-row pool; paid animal evaluation uses disjoint rows, with shared underlying types disclosed.

[PAID_PLANS.md](PAID_PLANS.md) records the approved $50 budget and groups of eight. [LEARNABILITY.md](LEARNABILITY.md) is the current gate report. Work is stopped pending a learnability decision. Main options S and U will be priced after measuring pilot learning speed. [PRIOR_WORK.md](PRIOR_WORK.md) stays as context; this is a side project for GitHub and X.

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
```

These commands use saved traces and request metadata, without service calls or credentials. The tokenizers use pinned local files or download those files from Hugging Face. `build_paid_plans.py` rebuilds the historical Phase 1 proposals; `build_approved_plan.py` reprices the approved group-size changes. [The reproduction check](results/phase2/reproduction.json) confirms analysis is identical without local run caches. The live runner is `scripts/run_phase2.py`; completed games and saved request IDs prevent resubmission. Training still needs the next gate approval. `.env` is ignored and untracked.

## Read the code

[LEARN.md](LEARN.md) explains each completed phase. Start with [worlds.py](twenty_bits/worlds.py), [predicates.py](twenty_bits/predicates.py), [information.py](twenty_bits/information.py), and [game.py](twenty_bits/game.py), then read [baselines.py](twenty_bits/baselines.py). The public observation is built in [prompts.py](twenty_bits/prompts.py), and frozen-game checks live in [evaluation.py](twenty_bits/evaluation.py).

[PROTOCOL.md](PROTOCOL.md) fixes the grammar, budget, posterior, metrics, and stopping rules. [NUMBERS.md](NUMBERS.md) records the main comparisons. EIG is measured and never rewarded. Legal name enumeration remains allowed, and the approved output cap accommodates the measured half-candidate lists. The final RESULTS.md will tie model claims to charts, paired CIs, spend, and failed attempts after those data exist.

The paid bridge lives in [model_player.py](twenty_bits/model_player.py), [tinker_rendering.py](twenty_bits/tinker_rendering.py), and [tinker_transport.py](twenty_bits/tinker_transport.py). The transport persists IDs before sampling, reserves the full declared cost, and handles pending retrieval without repeating sampling.
