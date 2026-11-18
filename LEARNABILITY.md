# Learnability gate

Completed 2026-11-18. The 32-game prompt-only probe is complete. No SFT, RL, optimizer update, or extra reference evaluation ran. Training is not approved.

The prompt change gives Qwen one win at N=8 and none at N=16. Valid-turn rates remain 22.2% and 9.9%. Most invalid questions still use table column codes instead of full attribute names. Recommend a short grammar warm start, followed by a qualification check, before any RL. Prompt and size both differ from Phase 2, so the probe is not a controlled estimate of the prompt's effect.

## What the probe actually ran

Qwen3-8B, thinking disabled, 2,048 output tokens, temperature 0.7, top-p 1, top-k disabled, p=0. Sixteen training-pool games each at N=8 and N=16 use seed 20261118 and independent generation seeds per turn. The public table, game rules, grammar, reward and answer-only feedback stay intact. Three worked grammar examples use random attributes, selected without reading column values, target or posterior. No remaining-candidate list is supplied. Frozen prompts, subsets, targets and hashes are unchanged.

Native and cookbook token sequences matched all 32 initial prompts and 224 example-action histories before sampling. Every real probe prompt was checked again before dispatch. Initial prompts and full-cap hold estimates are in the [rendering proof](research/learnability_probe_rendering.json). The complete run's preflight sum of per-call maximum holds was $0.748178. The independent probe cap is $1.50 including active holds. It is checked before each operation as well as the existing $50 project guard.

| N | Games | Valid turns [game-bootstrap CI] | Wins [Wilson CI] | Usage USD/game | EIG/Q | Questions/win | Truncated turns |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 16 | 24/108 = 22.2% [5.5%, 43.8%] | 1/16 [1.1%, 28.3%] | 0.00044144 | 0.061171 | 5.00 | 0.0% |
| 16 | 16 | 14/142 = 9.9% [0.7%, 23.6%] | 0/16 [0.0%, 19.4%] | 0.00390625 | 0.023990 | undefined | 19.0% |

Valid turns include a parsed counted ASK or a one-line GUESS of a listed candidate. A legal wrong guess counts as valid format. Additional ASK output in the final-guess slot is not valid. EIG includes invalid questions and losses. All confidence intervals resample whole games 10,000 times, except the stated Wilson win intervals. The one win is a genuine singleton: the model asked `fur`, `NOT hairless`, `NOT aquatic`, `NOT reptile`, and `NOT white`, then guessed `adult_male_polar_bear`. The exact posterior had one remaining item. That example is a development observation, not a typical-game claim.

Recorded usage is **$0.069563**, plus **$0.005618 held**. The cost/game values above exclude unresolved originals and include all completed-game turns. [All cell metrics, token counts, intervals and verification](results/learnability_probe/summary.json), [saved games](results/learnability_probe/games.jsonl.gz), and [request metadata](results/learnability_probe/requests.jsonl.gz) are available. Reported cache-hit tokens are response measurements; future forecasts give caching no credit.

## Fix options, from less to more change

**a. Clearer prompt and random grammar examples.** This is the probe already run. The rules explicitly distinguish full attribute names from storage codes. Its spend above is measured. The only model changes were public prompt wording and examples. It did not fix code-as-attribute errors well enough to start RL confidently.

**a plus remaining-candidate feedback.** This is a separate task. After each noiseless answer, a script would reveal posterior support as a list of names. Replaying observed probe actions with that added list gives an estimated **$0.0158 extra input cost for 32 games**, before margin. This is only a token counterfactual; no such policy was sampled, and its changed actions could cost more. At p=.10 all items retain positive posterior mass, so useful posterior-weight feedback would be yet another task change. Do not use this option for the main experiment without a separate decision.

**b. Random-question format SFT.** The offline proposal contains 554 per-turn examples from 128 fresh procedural toy games at N=4 and N=8. Select single attributes uniformly with replacement, independently of target, posterior or EIG. Use varied column prevalences, drop constant columns and enforce unique rows. Include a correct GUESS only at singleton. Ambiguous games contribute questions and no oracle guess. Supervise only the current assistant action, while charging the full context for training. Two passes, batches of 32, give 36 updates and 413,627 full-context tokens per pass. The gradient forecast is $0.363992, or **$0.70 with 1.5x margin and storage**. Dataset construction and supervision-prefix parity are offline; no training ran.

This teaches action syntax, stopping, and table/answer tracking. It supplies no EIG ranking or selected bisection examples. It also supplies a single-attribute action prior, so a pre-RL warm-start control is necessary before attributing that preference to RL. Fresh toy worlds reuse no held-out or frozen rows. However, synthetic SFT exposes the model to random-table identification, so later synthetic transfer must be described as new tables, labels and sizes, rather than a wholly unseen task. An animals-only warm-start variant would preserve the held-out-domain boundary and needs its own priced dataset if preferred. [SFT proposal and exact price](research/format_warmstart_price.json), [proposed examples](experiments/format_warmstart_proposal.jsonl.gz).

**c. Begin at N=4, then N=8.** This changes the training curriculum, with the same `2*ceil(log2 N)` question limit and unchanged reward. It has no separate setup charge. Under the measured token proxy, a group of eight costs the amounts in [learnability_forecast.json](research/learnability_forecast.json), including sampling and full-context gradients. Smaller N improves the reward signal of valid random play; it cannot repair invalid syntax by itself.

## How often random valid play wins

These estimates apply to a grammar-valid random single-attribute policy under options a and b; syntax training alone does not imply the LLM follows that policy. The same table prices the sizes introduced by c. Each size and noise mode has 500 training-pool start states and eight independent policy RNGs per state, 4,000 games. It asks attributes uniformly with replacement. It guesses at singleton, noisy confidence .95, or the budget, using a stable MAP tie break. Intervals resample start states. The singleton column removes wins from lucky final guesses among several candidates. Noisy posterior support never becomes singleton.

| N | Random-valid win p=0 [95% CI] | Win with singleton p=0 | Win p=.10 | Mixed-win groups p=0 | Nonzero-return groups p=0 |
| --- | --- | --- | --- | --- | --- |
| 4 | 89.7% [88.2%, 91.0%] | 80.2% | 77.4% | 40.4% | 99.8% |
| 8 | 76.3% [74.2%, 78.2%] | 58.2% | 59.8% | 68.6% | 99.0% |
| 16 | 57.7% [55.2%, 60.2%] | 38.0% | 42.0% | 80.0% | 95.4% |
| 32 | 41.7% [39.2%, 44.2%] | 24.5% | 29.4% | 85.2% | 89.0% |
| 64 | 28.0% [25.8%, 30.4%] | 13.7% | 17.7% | 73.4% | 75.2% |
| 128 | 18.6% [16.7%, 20.7%] | 6.8% | 11.3% | 57.2% | 57.2% |

The grouped simulation shares each start and seeded noise schedule. It measures the scripted policy, not Qwen's group variance. The paid probe samples one rollout per start, so it cannot directly establish GRPO group statistics. [Simulation data and settings](results/diagnosis/random_valid.json).

## Proposed A-only pilot, not authorization

Use the format warm start only if approved, then check 32 fixed development games from the animals training pool, 16 each at N=4 and N=8. Use a namespace distinct from this probe and the frozen bank. Propose at least 90% valid turns and 8/32 wins before RL. If that qualification fails, stop after SFT and development sampling.

If it passes, run seed 11 with one group of eight games per update. Each group shares one start state. Use N=4 for four updates, N=8 for eight, and N=16 for four: 16 updates and 128 training games. The proposed LoRA rank is 32 and AdamW learning rate is 1e-4 for both stages, with assistant-only loss weights for SFT. Record and freeze the remaining optimizer settings before an approved run. Standardize each group's returns with population SD and explicitly produce zero advantages for a constant-return group. Reward remains +1 win, -0.03/question, -0.1/INVALID. EIG never enters the reward.

Evaluate the same 32 development games at updates 0, 4, 8, 12 and 16. This gives 160 development rollouts and 16 training-curve points. Development results are not confirmatory frozen-eval results. Keep the scheduled endpoint; do not choose a checkpoint by frozen scores.

**Required stop rule:** after four updates, halt if fewer than 25% of groups have nonzero total-return variance, using variance greater than 1e-12. With one group per update, zero of four groups halts; one of four is exactly 25% and passes. Also report mixed-win groups and total wins. Question and invalid costs can make return variance nonzero with zero wins. I recommend an additional zero-wins stop after those 32 training games, subject to approval of the proposed configuration.

| Proposed work | Measured-token proxy with 1.5x margin | 2048-output scenario with 1.5x margin |
| --- | --- | --- |
| 16-update A pilot without SFT | $1.81 | $12.69 |
| Format SFT, qualification, then 16-update A pilot | $2.51 | $13.38 |
| Stop after SFT and qualification | $0.74 | $1.39 |
| Stop after four RL updates, including SFT | $1.05 | $3.46 |
| One full 280-game endpoint | $8.42 | $22.15 |

These forecasts use measured output tokens per call, measured native prefixes, the full question budget plus guess, full per-turn contexts for gradients, and no cache discount. N=4 borrows N=8 output lengths. Larger eval sizes borrow N=16 lengths, which is an untested extrapolation. The stress column assumes full 2,048-token outputs until a context-limit loss. It is a scenario rather than a guarantee of successful games. Storage allowances are $0.10 for SFT and $0.10 for the pilot. Use ephemeral fixed-weight sampler copies between updates and at most five named pilot snapshots plus one SFT snapshot, each bounded at 64 GB with a two-hour TTL. Their storage bounds are $0.088889 and $0.017778 at $0.10/GB/month. Download retained weights before expiry. Optimizer-state checkpoints are not included. Reserve storage before any save. Calls still reserve the larger of 1.5x estimated cost and their token-limited maximum.

Endpoint evaluations remain expensive relative to this small pilot. The primary RL control must be the pre-RL policy under the same prompt on the same 280 frozen cases. With SFT, that is the warm-start checkpoint; without SFT, it is the newly prompted raw base. A separate raw-base versus warm-start ablation is optional and costs another full evaluation. Existing Phase 2 scores remain historical and cannot isolate RL under a changed prompt. Leave the bank unchanged and add a separately approved prompt-version hash manifest. Do not start those evaluations now. Price main-run seed/update options after observing pilot learning speed and replacing these behavior-dependent estimates. These forecasts do not guarantee that both earlier seed options will fit.

## Network interruption and collection repair

Four original turns have no usable output. Three eventually returned `response expired`; one returned 404. The user approved four exact replacements with unchanged prompts, seeds and settings, retained **$0.005618** until billing resolves it, and permanently excluded original outputs. [Approval and signatures](research/learnability_probe_incident.json) preserve that record. All four replacement signatures match. The older five Phase 2 orphans still hold $0.007195.

| Request suffix | Receipt saved | Dispatch to collection attempt | Dispatch to terminal recovery reply | Dispatch to explicit inspection | Result |
| --- | --- | --- | --- | --- | --- |
| 57 | False | 9782.28s | no terminal body | 163.72 min | 404 |
| 56 | False | 10128.71s | 168.83 min | 169.48 min | response expired |
| 54 | True | 2.02s | 165.84 min | 169.52 min | response expired |
| 55 | True | 1.48s | 165.83 min | 169.52 min | response expired |

The elapsed times are local UTC dispatch-to-observation ages, not server retention times. Server completion and deletion timestamps are not exposed. The two acknowledged futures were polled within two seconds, then encountered repeated network failures over a long wall-clock interval. The receipt-less accepted request was not collected until the runner restart. No evidence says the model was generating during those hours. Reconnection and collection were not coordinated across all pending requests.

The probe runner now pauses producers on a connection error, drains active HTTP operations, recreates the client automatically and collects every recoverable saved future concurrently before any new sampling. Startup recovery even precedes capability checks. One unavailable future cannot prevent collection of the others. A 408 still means pending and re-polls the same request ID with its hold retained. Every submission saves its deterministic request ID before dispatch and verifies the receipt. New journals record collection-start and response-received times. Heartbeat shutdown waits for active work through a stop event. It does not cancel HTTP requests. Expired payloads remain unrecoverable; originals stay held and excluded. Recovery behavior is exercised with mocked SDK requests; the replacement run had no further network interruption.

## Spend and gate

Project usage is **$5.862788**, held costs are **$0.012813**, and **$44.124399 remains** under $50. Token-usage costs are gross estimates from observed response counts and the verified published rates; final invoices are pending. The proposed warm start and pilot fit the remaining budget under both forecast columns, but neither is authorized. Stop here for the user's decision.

Reproduce the offline work with `scripts/diagnose_phase2.py`, `scripts/measure_random_learnability.py`, `scripts/price_format_warmstart.py`, `scripts/summarize_learnability_probe.py`, `scripts/analyze_probe_recovery.py`, `scripts/reprice_learnability.py`, and `scripts/write_learnability_report.py`, using `.venv/bin/python`. The runner resumes saved probe games with zero service calls once all 32 are present. [Phase 2 diagnosis](DIAGNOSIS.md) contains the per-cell turn, error, termination and cost tables, plus three full transcripts. [Validation](results/learnability_probe/validation.json) and [offline reproduction](results/learnability_probe/reproduction.json) record the checks.
