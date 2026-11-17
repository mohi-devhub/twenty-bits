# Phase 0 gate report

Completed 2026-11-17. Stop here and wait for the user. No Phase 1 environment, paid evaluation, or training has started.

## What was built

- [PRIOR_WORK.md](PRIOR_WORK.md) compares thirteen relevant works and proposes sharper measurements where the ideas already exist.
- [TINKER_CHECK.md](TINKER_CHECK.md) documents the existing cookbook recipe, exact reuse boundaries, source revisions, model choices, billing behavior, and 408 handling.
- [ledger.json](ledger.json) and [budget.py](twenty_bits/budget.py) reserve at least 1.5 times estimated cost before dispatch and refuse work beyond $30. Unknown costs stay held.
- [costs.py](twenty_bits/costs.py), the saved rate card, and [cost_projection.json](research/cost_projection.json) make the per-phase estimates reproducible offline.
- [DESIGN_NOTES.md](DESIGN_NOTES.md) records unresolved experimental definitions and the world-size conflict. [LEARN.md](LEARN.md) explains the Phase 0 code.

The repository was initialized locally. No upstream project code was copied into this repository, and no remote was created or pushed.

## Verification

`python3 -m unittest discover -s tests -v` passes **26 tests**. They cover exact money arithmetic, the margin, per-call maxima, cap refusal before callbacks, crash holds, request-ID preservation, actual-cost reconciliation, process concurrency, and hand-counted token costs.

These are budget and estimator tests. The Phase 1 parser, answerer, entropy, and world tests do not exist yet. The 408 test uses a fake submission and ledger state, not a live Tinker request.

Ruff lint and formatting checks pass. The saved rate-card hash, all 39 inventory rows, local document links, and regenerated projection were checked against the committed files.

`python3 -m twenty_bits.budget status` reports $0 spent, $0 held, and $30 available. The full Phase 2 preflight is refused without changing the ledger. The cost projection regenerates from the saved rate card.

## Key numbers

| Quantity | Result |
| --- | --- |
| Tinker actual spend / cap | **$0.00 / $30.00** |
| Tinker service requests | 0 |
| Current outstanding holds | $0.00 |
| Published catalog IDs | 39, including 3 that conflict with the retirement list |
| Live account capabilities | Unverified because credentials and SDK are absent |
| Proposed main model | `Qwen/Qwen3-8B` |
| Proposed zero-shot-only reference | `openai/gpt-oss-120b` |
| Small-model games per full evaluation | 8,000 |
| Six final-checkpoint evaluation games | 48,000 |
| Small-model full evaluation, expected without cache | $45.69 |
| Six final evaluations, optimistic all input cached | $75.48 |
| Full illustrative project, expected without cache | $386.47 before margin |
| Smaller unapproved diagnostic | $17.73 expected; $26.60 with 1.5 planning margin |
| Maximum EIG at p=0 | 1 bit per binary answer |
| Maximum EIG at p=0.10 | 0.5310044064 bits per binary answer |

Cost estimates depend on explicit token and training-length assumptions in [BUDGET.md](BUDGET.md). They are not measurements or guarantees. No game win rates have been measured.

## Surprises and decisions at this gate

RL on 20Q, EIG-based question training, domain transfer, and exact-table search references all have prior work. The proposed study should claim a controlled outcome-based RL measurement, not novelty for those ingredients.

The cookbook's group advantages are centered but not standardized. Its answerer is an LLM, and its wrong guesses do not end the episode. Those defaults must be adapted to the requested protocol.

The public price catalog lists three models that the official deprecations page says are retired. The recommendations avoid those entries, but authenticated capabilities remain necessary before a paid run.

Two choices need resolution before the relevant work:

1. **World size before Phase 1.** N=256 cannot be sampled from the requested 150 to 200 items. The proposal is at least 300 unique rows per world, with an explicit choice of whether animals training uses about 200 or the full enlarged pool.
2. **Paid scope before Phase 2.** Preserve the $30 cap. The full requested study is not affordable under the planning assumptions. Approve a smaller diagnostic or defer paid phases until a concrete measured-token plan fits. The reduced sample counts in BUDGET.md are not active.

The remaining rule and stopping definitions in DESIGN_NOTES.md can be settled during offline Phase 1 before the evaluation protocol is frozen. Next step, after the user resumes, is that offline phase. Append its learning notes, run its required tests and baselines, commit, and stop again.
