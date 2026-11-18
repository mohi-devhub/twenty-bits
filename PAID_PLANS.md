# Approved $50 budget and Phase 2

The later learnability gate is [LEARNABILITY.md](LEARNABILITY.md). The authorized $1.50 prompt probe completed 32 games for $0.069563 in recorded usage, with $0.005618 in additional unresolved holds. Total project usage is $5.862788, holds are $0.012813, and $44.124399 remains. Its [new forecasts](research/learnability_forecast.json) supersede the Phase 2 pilot proposal below. No SFT or RL is approved. Main-run seed/update options still wait for measured pilot learning speed.

The user approved a $50 total cap, including active holds, on 2026-11-18. Phase 2 uses Qwen3-8B with thinking disabled, a 2,048-token output cap, 28 games in each of ten frozen cells, and a 20-game gpt-oss-120b reference. The 4B screen was dropped. [phase2.json](evals/phase2.json) fixes the sampling configuration. Training is not authorized yet.

All pilot and main groups now contain eight games. The next training gate proposes condition A only. At the pilot gate, Option S retains A seeds 11, 23, 37 and B seeds 41, 53; Option U uses A seeds 11, 23 and B seed 41. Update counts and the recommendation will use measured learning speed and the remaining budget. A visible learning curve takes priority over additional seeds.

[approved_plan.json](research/approved_plan.json) reprices the approved changes. Phase 2 forecasts $2.95805922 before margin and $4.43708883 with margin. Its conservative uncached token-cap envelope is $17.647606. The earlier 32-update, five-seed schedule with groups of eight and an A-only pilot would cost $66.81 with margin, so it is not an active main-run plan. The measured output lengths will replace the earlier 64-token training forecast at the Phase 2 gate.

The five uncertain submissions from the adapter incident remain **orphaned, possibly billed**, with $0.007195 held. Their outputs are permanently excluded. The user authorized five exact replacements with the same prompts and sampling seeds. [Incident and authorization](research/phase2_incident.json) records the request mismatch and recovery rules. The ledger's reservation and 408 rules still apply.

## Historical Phase 1 proposals

Both proposals use the measured native chat-template token counts in [token_measurements.json](research/token_measurements.json), the pinned [tokenizers](research/tokenizers.json), and the published [Tinker rate card](https://tinker-docs.thinkingmachines.ai/tinker/models.json). All arithmetic and sample-size assumptions are reproducible with `python3 scripts/build_paid_plans.py`.

The tables below preserve the Phase 1 proposals, which used four games per group and included a 4B screen. Their $30 cap status and output-length assumptions describe that earlier gate. They are superseded by the approval above.

## Workloads and costs

| Choice | Plan 30 | Plan 50 |
| --- | ---: | ---: |
| Recommended main policy | Qwen/Qwen3-8B | Qwen/Qwen3-8B |
| Frozen cells | 10 | 10 |
| Games per cell per primary checkpoint | 24 | 28 |
| Games per complete primary evaluation | 240 | 280 |
| Main condition A seeds | 2: 11, 23 | 3: 11, 23, 37 |
| Main condition B seeds | 1: 41 | 2: 41, 53 |
| Updates per main seed | 32 | 32 |
| Groups/update × games/group | 1 × 4 | 1 × 4 |
| Main training games | 384 | 640 |
| Pilot updates A / B | 24 / 8 | 32 / 16 |
| Pilot training games | 128 | 192 |
| Pilot development checks | 48 games total | 48 games total |
| Kept/evaluated endpoints per main seed | 1 | 1 |
| Evaluated main endpoints | 3 | 5 |
| Primary base evaluations | 1 | 1 |
| Primary evaluation games, base plus endpoints | 960 | 1,680 |
| Alternative 4B zero-shot screen | 50 matched games | 50 matched games |
| gpt-oss-120b zero-shot reference | 20 games | 20 games |
| Forecast before margin | **$19.52** | **$32.34** |
| Forecast × 1.5 | **$29.28** | **$48.51** |
| Headroom after that margin | $0.72 | $1.49 |

The primary slices are indices 0 through 23 or 27 in every cell, unchanged across seeds and checkpoints. Half of the ten cells have p=0.10. Conditions A and B use the same 32-update curriculum, eight updates each at N=16,32,64,128, with fresh initialization from the base model for each seed. A uses truthful answers and B uses p=0.10. Pilots use N=16 and 32 and are discarded before main runs. No checkpoint is selected by frozen-test performance.

Plan 50 spends the extra allowance on independent seeds and slightly denser cells. There are no extra main evaluation checkpoints. EIG over training comes from the logged training trajectories, clearly labeled as such; the frozen set compares the base with scheduled endpoints. Tools and foods have no paid allocation. Additional paid cells require remaining budget and another gate.

| Phase | Plan 30 | Plan 50 |
| --- | ---: | ---: |
| 0 and 1, offline | $0.00 | $0.00 |
| 2, primary base plus 4B screen and reference | $3.40 | $3.80 |
| 3, pilot training and development checks | $1.39 | $1.99 |
| 4, main training | $7.52 | $12.54 |
| 4, endpoint evaluations | $7.20 | $14.01 |
| 5, analysis and exports | $0.00 | $0.00 |
| Total before margin | $19.52 | $32.34 |

Phase gates remain in force. Approval starts Phase 2 only. The pilot and its audit get another stop before main training.

## Model choice and ability check

On the saved rate card, Qwen3-8B costs less than the supported 4B option, Qwen3.5-4B:

| USD per million tokens | Qwen3-8B | Qwen3.5-4B |
| --- | ---: | ---: |
| Uncached input | $0.195 | $0.330 |
| Cached input | $0.039 | $0.066 |
| Output | $0.600 | $1.005 |
| Training | $0.440 | $0.737 |

The older Qwen3-4B-Instruct-2507 is retired in the checked documentation. Task-specific zero-shot ability is **unknown** because Phase 1 makes no Tinker calls. Parameter count and another benchmark cannot establish ability in this grammar. Recommend 8B on known cost, then check ability before training. The budget includes five matched frozen games per cell for the 4B alternative, compared with the matching base-8B slice. That small screen can expose gross format or search failures; it cannot reliably rank close models. If it suggests switching, stop at the Phase 2 gate and reprice the chosen model rather than silently training 4B at 8B rates.

The reference uses five games in each of the four N=32 domain/noise cells. Its 512-token output cap includes reasoning. Report truncation and format failures beside its score. This is a limited sanity reference, not a controlled parameter-count experiment. It fits both forecasts, but is expendable at a later gate if real usage leaves less room.

## What the token measurements cover

The native tokenizers were downloaded, not model weights. Counts cover all 2,000 frozen public prompts. Played-trajectory measurements use eight greedy-predicate games per cell per tokenizer. Training-prefix measurements use forty sampled training-pool subsets per size and model.

| Domain and N | Mean initial Qwen3-8B prompt tokens |
| --- | ---: |
| Animals, 32 | 1,083 |
| Animals, 128 | 3,162 |
| Relabeled synthetic, 32 | 945 |
| Relabeled synthetic, 128 | 2,692 |
| Relabeled synthetic, 256 | 5,027 |

The sparse table lists true column codes and maps those codes to full attribute names in its header. This keeps a stable prefix without requiring hexadecimal or base64 decoding. The exact public prompts are hashed in evals/frozen/prompt_hashes.json.

For forecasts, use the **maximum** measured initial prompt in each cell, the full question budget plus a guess, 64 generated tokens per turn, and another 32 tokens per prior turn for chat and answer overhead. Charge training for separate full per-turn contexts, including masked prompt tokens. This is deliberately more input work than an efficient short winning game. Give caching no cost credit.

The primary universal output cap is 2,048 tokens with Qwen thinking disabled. It leaves room for legal half-candidate name lists: the measured actions use 146 to 1,409 tokens across the paid sizes. Thus the strategy audit is not silently forced to reject those lists. The 64-token forecast is not the output cap. Repeated long or malformed outputs can exceed the forecast. The 1.5 margin is an estimate buffer, not a bound on every possible trajectory.

Before each actual operation, the existing ledger still reserves the larger of estimate times 1.5 and the call's token-limited maximum. Reconcile actual usage and retain pending holds. If calls will not fit, stop with the approved protocol intact; do not quietly drop games, change caps, or resubmit timed-out work. These schedules are affordable forecasts, not a guarantee that any behavior at the universal cap completes the entire schedule.

## Caching applies, but hits remain unmeasured

Tinker supports [cached prompt prefixes within a sampling client](https://tinker-docs.thinkingmachines.ai/tinker/howto/inflight_sampling/) and exposes [prompt_cache_hit_tokens](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/types/sampleresponse/). The table precedes noise settings and dialogue, so repeated turns and grouped games can reuse it. The exact Qwen3-8B prefix shared between the paired N=32 noise modes is recorded in token_measurements.json. Separate checkpoint clients and cache eviction can remove those savings. No service call has verified hits for this project, and both plans assume none.

The Phase 2 adapter must check that cookbook rendering matches the measured native token sequences before any paid sample. A tokenizer measurement does not prove account-specific model availability, cache behavior, or billed usage.

## Precision expectations

These are **full widths** of approximate 95% intervals for one checkpoint, before between-training-seed uncertainty. Win-rate widths use the conservative p=0.5 case. The pooled calculation treats the two noise settings as a matched case pair, so it has 5 times the games-per-cell independent units, not 10 times. EIG and questions/win proxies use the observed greedy-predicate game variation; the LLM's variation may be much larger.

| Measurement | Plan 30 | Plan 50 |
| --- | ---: | ---: |
| Win-rate width in one cell, conservative | 40.0 percentage points | 37.0 percentage points |
| Win-rate width pooling ten cells, preserving paired noise cases | 17.9 points | 16.6 points |
| Paired win-change width in one cell, conservative | Up to 80.0 points | Up to 74.1 points |
| EIG width per cell, baseline-variation proxy | 0 to 0.0187 bits | 0 to 0.0173 bits |
| Questions/win width, baseline-variation proxy | 0 to 2.12 questions | 0 to 1.96 questions |
| Noisy re-ask-rate width if baseline opportunity frequency holds | About 65 points | About 60 points |

The re-ask forecast is weak because the baseline produces only 0.075 unlikely-answer opportunities per noisy game across the five paid noise cells. That gives roughly 9 or 10.5 opportunities per checkpoint in these plans. Report the actual denominator and avoid a strong conclusion from a small count. A model with worse splits can generate more opportunities; that also changes what the rate means.

Between-seed uncertainty is separate. If EIG varies by SD=0.02 across seeds, a t-based 95% interval for the mean has full width about 0.359 bits with two seeds and 0.099 bits with three. One B seed in Plan 30 gives no between-seed interval. Two B seeds in Plan 50 still provide a weak estimate. These are sensitivity calculations, not measured model variance. Final reports use paired game bootstraps and seed-level estimates as specified in NUMBERS.md.

Neither plan supports fine claims within every cell. Plan 50 gives a more useful check that an A result repeats across seeds and gives B an independent repetition. The comparison is about effect sizes and visible strategies, with uncertainty retained.
