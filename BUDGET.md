# Budget and feasibility

The hard cap is **$30 of total project Tinker usage**. Current actual spend is **$0.00**, outstanding reservations are **$0.00**, and no service calls have been made. Public web research does not create Tinker usage.

## The requested schedule does not fit the current estimate

Four domains, five candidate sizes, and two noise settings create 40 cells. At 200 games per cell, one small-model evaluation requires 8,000 games. Six final checkpoints require another 48,000 evaluation games before any intermediate checkpoints.

The table below uses the saved [rate card](research/tinker-models-2026-11-17.json). The [estimator](twenty_bits/costs.py) produces [all unrounded numbers and assumptions](research/cost_projection.json).

| Phase | Expected, no cache savings | Optimistic, all input cached | Stress, no cache savings |
| --- | ---: | ---: | ---: |
| 0: research, ledger, tests | $0.00 | $0.00 | $0.00 |
| 1: offline worlds and baselines | $0.00 | $0.00 | $0.00 |
| 2: small model 8,000 games and reference 800 games | $53.30 | $14.58 | $139.97 |
| 3: pilot and small evaluation slices | $3.79 | $1.81 | $10.62 |
| 4: six training runs and six full final evaluations | $329.38 | $118.15 | $874.24 |
| 5: offline analysis and write-up | $0.00 | $0.00 | $0.00 |
| Total before reservation margin | **$386.47** | **$134.54** | **$1,024.82** |
| Total times 1.5 | $579.70 | $201.80 | $1,537.23 |

Phase 2's small model alone costs $45.69 in the no-cache scenario. Phase 4's six final evaluations alone cost $75.48 even in the optimistic cached scenario. More saved checkpoints add more full-grid evaluations. Main-run length is unspecified in the request, so the training totals above use an explicit illustrative length, not a promised minimum or an approved run.

These estimates are not observed bills. Caching, shorter conversations, and compact tables may reduce them. Truncation, long reasoning, failed games, training on multiple full-prefix datums, and retries that accidentally resubmit work may increase them. The cached column optimistically discounts every input token, including first turns. It is not a guaranteed discount. None of these scenarios justifies starting the full study under $30.

## Token assumptions

The main model is `Qwen/Qwen3-8B`. The reference is `openai/gpt-oss-120b`, with 20 reference games per cell for this projection.

- A prompt contains `512 + 24*N` tokens for the rules, attribute header, names, and compact table rows. Actual table tokenization is still pending.
- An expected successful game uses `log2(N)` questions and one final-guess turn. Each turn generates 128 tokens including visible reasoning and action.
- Each earlier turn adds those 128 output tokens and 32 tokens of answer and chat overhead to later inputs. The entire table and history are billed again on each turn unless cached.
- The stress scenario uses `2*log2(N)` questions, a final guess, and 256 output tokens per turn. These are planning assumptions, not frozen output caps.
- Pilot training has 32 updates, two groups per update, four games per group, split equally between N=16 and N=32. Two evaluation slices each use five games per cell, or 400 games combined.
- Each of six main runs has 100 updates, two groups per update, four games per group, and equal allocation across training sizes. Keep only one final checkpoint per run in this projection.
- Training cost conservatively allows separate full-prefix datums per turn. Prompt masks prevent prompt prediction loss, but do not make prompt processing free.
- Storage is assumed free. An unknown or paid storage plan must be priced separately before saving anything.

The repeated input count is `T*P + (O+32)*T*(T-1)/2`. Sampling cost is `(input*prefill_rate + output*sample_rate)/1,000,000`. Cached and uncached input rates differ. Training cost uses actual datum token counts at the training rate when running, not only tokens carrying nonzero loss.

Reproduce the projection without contacting Tinker:

```bash
python3 -m twenty_bits.costs --output research/cost_projection.json
```

## A smaller option for review

The $30 cap remains fixed. One possible diagnostic keeps all domains, all sizes, both noise settings, and three seeds for each training condition. It changes the sample sizes and training lengths, so it needs approval before replacing the requested study.

| Phase | Proposed diagnostic workload | Expected no-cache cost |
| --- | --- | ---: |
| 0 and 1 | Research and full offline baselines | $0.00 |
| 2 | 5 games per cell for each model, 400 games combined | $3.04 |
| 3 | 32 updates, 1 group of 4 games per update at N=16 or 32; two 40-game eval slices | $1.21 |
| 4 | 6 runs, 24 updates each, 1 group of 4 games; 5 games per cell at each final checkpoint | $13.48 |
| 5 | Offline analysis | $0.00 |
| Total | 704 training games and 1,680 evaluation games | **$17.73** |
| Total times 1.5 | Planning margin, not authorization | **$26.60** |

Five games per cell gives weak cell-level inference. This would be a learning project and diagnostic, not evidence equivalent to the requested 200-game study. Tokenization and pilot measurements can still reject it. The full 200-game bank could be generated and frozen offline, but evaluating a subset must be explicitly labeled and approved.

No reduced protocol is active. The next authorized phase after its gate is offline Phase 1. Any paid phase still needs an affordable concrete plan.

## How the ledger refuses spending

[`ledger.json`](ledger.json) is the source of truth. [`twenty_bits/budget.py`](twenty_bits/budget.py) provides the guarded call boundary. It uses decimal USD, rounds upward to a microdollar, and enforces:

`settled_actual_costs + outstanding_holds + new_hold <= 30`

Each hold is `max(estimate*1.5, maximum_possible_call_cost)`. Requiring a maximum in addition to the requested estimate margin avoids treating an uncertain estimate as a guarantee. Before a real sample, derive its maximum from the rendered prompt, `num_samples`, output cap, and fresh uncached rates. Before training, count every datum token. Before storage, bound its lifetime and size.

The state sequence is `reserved`, then `dispatching`, then optionally `submitted` with a persisted request ID, then `settled` with actual cost and evidence. Only `reserved` work can be voided. A network exception leaves the entire hold in place. The original ID survives 408 polling; the reservation cannot be dispatched twice.

Separate process locks prevent concurrent reservations from exceeding the cap. Atomic JSON replacement prevents partial writes. A missing ledger, corrupt entry, changed cap, or recorded cost beyond the declared maximum blocks new submissions. If the provider reports an unexpected cost, the ledger records that truth and blocks further calls. It cannot reverse an already incurred charge.

Use `Ledger.call(send, ...)` for each submission, including zero-cost service operations. `Ledger.dispatch` writes the dispatch state before invoking the callback exactly once. This is a local budget guard, not a provider-side account limit. Raw SDK calls can bypass it; the Phase 2 integration must route every SDK operation through the guard before paid use. No SDK integration has been launched in Phase 0.

`Ledger.check_run` first rejects an unaffordable whole-run estimate and declared maximum. It does not consume money or replace per-call holds. The project uses one run coordinator; do not launch multiple schedules that each assume the same unreserved future balance.

Inspect the budget without making a service call:

```bash
python3 -m twenty_bits.budget status
python3 -m twenty_bits.budget check-run --estimate-usd 53.30165760 --max-cost-usd 139.96646400
```

The second command refuses with exit code 2 and leaves the ledger untouched. A run-level maximum is only valid after actual token counts and caps have been checked. The scenario stress total is useful for rejecting this plan, not certifying another plan's maximum.

## Reconcile before releasing holds

After work completes, save raw token usage, session IDs, rate snapshots, and billing evidence. Record final cost with `settle(actual_usd=..., evidence=...)`. Unknown costs remain held. Provisional current-day rates must not be mistaken for reconciled invoices. Hourly billing buckets can combine calls, so reconcile each attributable bucket once and document its allocation without double counting.

No usage has occurred to reconcile in Phase 0. The ledger therefore contains zero entries and $0 actual cost. Keep this ledger through every phase and commit it at each gate. Do not reset it when resuming or starting a new seed.
