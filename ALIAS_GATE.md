# Attribute aliases and qualification gate

The parser-only probe and conditional format SFT are complete. **Qualification failed on wins: 3/32, below the required 8/32.** Pooled valid turns were 92.0%, above the 90% format requirement. No RL update ran. Stop at this gate.

## Exact grammar aliases

`attribute-codes-v2` accepts each table-header code as an exact, case-sensitive alias for its full attribute name. Full names and codes can mix, for example `ASK: a AND NOT aquatic`. The renderer and parser derive codes from the same function after constant columns are removed. There is no fuzzy matching or case folding.

An identifier in an expression denotes an attribute. A name after `item ==` denotes a literal item, so a candidate called `a` does not change the meaning of the attribute code `a`. Lowercase keyword-like codes remain distinct from uppercase operators. A bare `item` is an attribute only if the header supplies that code; `item == name` remains equality. Headers with conflicting code/full-name meanings are rejected. Tests cover these collisions, mixed identifiers, exact case, malformed/malicious inputs, and alias remapping after constant-column removal.

Historical Phase 2 and the earlier prompt probe retain `names-v1` scoring. Their saved outcomes are not rescored under changed answers. Frozen games, world files, prompt hashes, reward and question budgets are unchanged. The probe uses identical public prompt bytes, subsets, targets, output cap and requested generation seeds to the earlier 16+16 games. In particular, the prompt still requests full names; the acceptance grammar now also understands codes. This run changes the parser, not the observation or instructions. [Rendering and hash proof](research/alias_probe_rendering.json), [grammar rules](PROTOCOL.md).

## Parser-only re-probe

Qwen3-8B, thinking disabled, 2,048 output tokens, temperature 0.7, top-p 1, top-k disabled, noiseless training-pool animals. There were 16 games each at N=8 and N=16, with game seed 20261118 and the same per-turn generation seed namespace. No remaining-candidate feedback was supplied.

| N | Valid turns [95% CI] | Wins [Wilson 95% CI] | EIG/question [95% CI] | Questions/win |
| --- | --- | --- | --- | --- |
| 8 | 80/95 = 84.2% [63.6%, 100.0%] | 1/16 [1.1%, 28.3%] | 0.3410 [0.2182, 0.4690] | 5.00 |
| 16 | 84/131 = 64.1% [40.0%, 86.2%] | 0/16 [0.0%, 19.4%] | 0.1764 [0.0881, 0.2778] | undefined |

Pooled valid turns were **164/226 = 72.6%**. The declared decision rule required at least 80% pooled valid turns and at least one N=8 win. It failed the format requirement and activated the user's conditional SFT approval. The probe cost **$0.082031**, with no unresolved probe holds, against the **$0.25** limit including holds. Its measured prior-run forecast was $0.069563, or $0.104345 with margin. No settings changed during the run.

These are all remaining invalid-turn causes. Parser errors and final-slot failures partition the invalid turns here; truncation is a separate flag in the saved summary.

| N | Remaining invalid-turn cause | Count |
| --- | --- | --- |
| 8 | Expected an attribute, NOT, parentheses, or item equality. | 1 |
| 8 | Expression nesting exceeds 64 levels. | 5 |
| 8 | Non-GUESS action after question budget | 2 |
| 8 | Unexpected trailing tokens. | 6 |
| 8 | Unknown attribute: horns | 1 |
| 16 | Expected ). | 9 |
| 16 | Expected an expression. | 9 |
| 16 | Expression exceeds the 4096-token parser limit. | 16 |
| 16 | Non-GUESS action after question budget | 6 |
| 16 | Unknown attribute: hook_beak | 7 |

[Probe metrics, intervals and verification](results/alias_probe/summary.json), [all games](results/alias_probe/games.jsonl.gz).

## The 303 other zero-EIG questions

All 303 were positive OR lists of item equalities. None was a singleton item equality on a remaining candidate. None was false for every remaining candidate. Their logical causes partition as follows, under the historical names-only grammar and saved posteriors.

| Logical cause | Questions | Repeated split/complement |
| --- | --- | --- |
| true_for_entire_table | 220 | 199 |
| true_for_every_remaining_candidate_only | 82 | 81 |
| nonconstant_but_nearly_certain_bayesian_mass | 1 | 1 |

The single noisy case had nonzero probability on both answers but expected information below 1e-12 bits. Repetition is a separate behavioral dimension: **281/303** repeat an earlier truth vector or its complement. It must not be added to the logical-cause counts. The other eight questions among the original 311 named only already-eliminated items, as previously reported. Unknown item names are invalid and are not part of the 311. [Every classified question and per-cell counts](results/diagnosis/zero_eig_other.json).

## Conditional format SFT

The condition failed, so the approved warm start ran once: seed 11, rank-32 LoRA with attention, MLP and output projection trainable, AdamW learning rate 1e-4, beta1=0.9, beta2=0.95, epsilon=1e-12, no weight decay or gradient clipping. There were two passes over the frozen 554-example proposal, batches of 32, and **36 optimizer updates**. The two shuffle seeds were 11 and 12. Full-context training input totaled **827,254 tokens**.

The dataset uses fresh procedural toy tables and random single-attribute questions with replacement. Correct guesses appear only at singleton. It contains no frozen games or held-out world rows. Native/cookbook supervision prefixes matched all 554 examples. The pinned cookbook helper creates shifted inputs and targets; only the current assistant action, including its stop token, has loss weight. Prompt tokens receive zero loss weight. No EIG ranking, bisection selection, outcome reward or RL advantage enters this cross-entropy stage.

Gradient usage cost **$0.364010**, versus $0.36399176 forecast. The difference is upward rounding across calls. Two bounded checkpoint-storage holds total **$0.100000** and remain until billing reconciliation. Both checkpoints have a two-hour TTL. The external adapter, 369,221,544 bytes, is downloaded under `runs/format-warmstart-v1/adapter/` with a SHA-256 manifest, so the local copy survives hosted expiry. The native and external checkpoint URIs are recorded in [completion.json](results/format_sft/completion.json).

Mean per-example action NLL was 0.3041 nats/token in epoch 1 and 0.1840 in epoch 2. This is training fit, not game success. [All update metrics](results/format_sft/learning_curve.json).

The SFT supplies a single-attribute action prior and table-tracking examples. Later RL comparisons must use this pre-RL checkpoint as their matched control. Toy-table exposure also changes synthetic transfer into a test of new tables, labels and sizes rather than an entirely unseen random-table task.

## Qualification before RL

The separate fixed development set has 16 training-pool animal games each at N=4 and N=8, seed 20261120 and indices 600000 through 600015. These games never entered gradients. The policy sampled from the trained snapshot, not a new base sampler. The output cap, disabled-thinking setting, grammar, reward, noise and answer-only feedback stayed fixed. These are development results, not a new frozen paid evaluation or a paired estimate of the SFT effect.

| N | Valid turns [95% CI] | Wins [Wilson 95% CI] | EIG/question [95% CI] | Questions/win |
| --- | --- | --- | --- | --- |
| 4 | 58/61 = 95.1% [87.7%, 100.0%] | 2/16 [3.5%, 36.0%] | 0.4883 [0.4033, 0.5892] | 3.00 |
| 8 | 68/76 = 89.5% [82.9%, 95.2%] | 1/16 [1.1%, 28.3%] | 0.4532 [0.3810, 0.5416] | 5.00 |

Pooled valid turns were **126/137 = 92.0%**. That passes the 90% format requirement. **3/32 wins fails the 8/32 requirement**, so qualification failed. Format validity did not establish reliable search. Confidence intervals resample complete games 10,000 times; win intervals use Wilson bounds. Undefined win-conditioned quantities remain null.

| N | Remaining invalid-turn cause | Count |
| --- | --- | --- |
| 4 | GUESS name outside candidate table | 1 |
| 4 | Unknown attribute: adult_female | 2 |
| 8 | GUESS name outside candidate table | 1 |
| 8 | Non-GUESS action after question budget | 3 |
| 8 | Unknown attribute: adult_female_mallard | 1 |
| 8 | Unknown attribute: herivore | 1 |
| 8 | Unknown attribute: large_tongue | 1 |
| 8 | Unknown attribute: sprays | 1 |

The free consistency audit found 17 guesses of already-eliminated candidates, including 8 wrong guesses despite a singleton posterior. 13 games reached a singleton, but only 2 of those won. There were 2 guesses outside the table. Of the three wins, 2 had a singleton posterior and 1 did not. The scripted greedy-predicate policy won **32/32** on the same qualification cases, averaging 2.50 questions and 1.0000 expected bits/question. These cases are solvable under the environment rules.

One selected consistency failure, `train-v1/seed20261120/animals/4/600002/p0`, had exactly `adult_male_short_beaked_echidna` remaining:

```text
ASK: adult -> YES
ASK: adult_female -> INVALID
ASK: adult_female -> INVALID
ASK: female -> NO
GUESS: juvenile_female_pelican -> LOSS
```

This example illustrates a failure and is not a performance sample. [Consistency audit](results/format_sft/behavior_audit.json), [qualification metrics and CIs](results/format_sft/summary.json), [complete games](results/format_sft/games.jsonl.gz).

## Budget and next gate

SFT plus qualification recorded **$0.370867** and holds **$0.100000**, safely inside the conservative **$2.51** combined cap including holds. Qualification sampling alone cost $0.006857. All operations used Ledger.call; 408 polling retains the original future and hold. Sampling IDs were durable before HTTP dispatch, and training receipts were durable before polling. No forward/backward or optimizer operation was repeated to recover a timeout.

Project usage is **$6.315686**, total holds are **$0.112813**, and **$43.571501 remains** under $50. The nine older excluded submissions still hold $0.012813. The additional $0.10 is checkpoint storage. Usage charges use observed response/request token counts and published rates, rounded upward per call; final invoices remain pending.

The gpt-oss-120b reference is removed from future plans. Its 20 completed games remain historical failure data because its capped reasoning consumed 157/220 turns without an action. No new reference call ran.

**No RL is approved or started.** The proposed 16-update A pilot remains N=4 for four updates, N=8 for eight, and N=16 for four, one group of eight games per update with independent member seeds and one common start state. Its required stop rule remains: after four updates, halt if fewer than 25% of groups have nonzero return variance. EIG remains measurement only. Do not lower the qualification threshold, extend SFT, change prompts, expose candidate support or start that pilot without a new decision. The next issue to resolve is guess consistency with the observed answers.

Reproduce offline with `.venv/bin/python scripts/break_down_zero_eig.py`, `scripts/summarize_alias_probe.py`, `scripts/summarize_format_sft.py`, `scripts/audit_qualification.py`, and `scripts/write_alias_gate.py`. The completed runners refuse to repeat paid work. [Validation](results/format_sft/validation.json) records unit tests, request verification and frozen-hash checks.
