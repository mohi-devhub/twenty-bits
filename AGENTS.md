# Twenty Bits working rules

Phase 2 and its learnability diagnosis are complete on 2026-11-18. The approved prompt probe completed 32 training-pool games: one win at N=8 and none at N=16. Read DIAGNOSIS.md and LEARNABILITY.md. No SFT or RL is authorized. The warm start, qualification check, and 16-update A pilot are proposals only. Stop until the user chooses. Append a short plain-language section to LEARN.md and commit at every phase gate.

The user approved a $50 total cap including holds on 2026-11-18; ledger.json records that approval. The cap constant and validation messages may reflect $50. Reservation, dispatch, settlement, and 408 behavior otherwise stay unchanged. Every Tinker operation, including metadata operations, goes through Ledger.call. Do not run the stock cookbook recipe or bypass the guard through its internals.

A retrieve_future 408 means pending work. Re-poll the original request_id and retain its hold. Never resubmit sampling, training, or optimizer work because polling times out. Unknown costs remain held until reconciled.

Five original entries are labeled orphaned, possibly billed. Keep their $0.007195 holds until billing resolves them and never use their outputs for actions, scoring, examples, or training. The user authorized five exact replacements; research/phase2_incident.json records them. Every new sampling request must save its deterministic request ID in the journal and ledger before HTTP dispatch, then verify the receipt. Drain active HTTP operations when stopping; do not cancel them to restart faster.

Four additional probe originals have expired or unavailable responses. The user approved exact replacements and permanent output exclusion in research/learnability_probe_incident.json. Keep their $0.005618 holds until billing resolves them. Total unresolved holds are $0.012813. On a network error, pause new submissions, drain HTTP operations, reconnect, and collect all recoverable saved futures concurrently before submitting anything new. Do not infer exact server deletion time from local observation timestamps.

Use training_game from twenty_bits/worlds.py for training. It accepts only animals, the fixed 200-row training pool, and N=4,8,16,32,64,128 after the learnability request. Frozen games and held-out rows never enter gradients. Tools, foods, and the saved synthetic world are transfer domains. The procedural format-SFT dataset is an unapproved proposal and would change the interpretation of synthetic transfer. The paired paid animals games use disjoint held-out profiles, not entirely unfamiliar underlying types.

Read PROTOCOL.md, PAID_PLANS.md, NUMBERS.md, and PHASE2.md before continuing. Freeze sampling settings before paid work and do not change rewards, caps, grammar, or evaluation protocol within a run. Stop and ask if a change is necessary. Preserve the common declared frozen slice across all models and checkpoints.

The prompt probe has its own immutable config and message builder. Frozen Phase 2 prompts remain unchanged. A future RL comparison needs its pre-RL control under the same prompt: the newly prompted raw base without SFT, or the warm-start checkpoint with SFT. A full separate SFT ablation is optional. Do not compare a trained policy under a changed prompt with the historical Phase 2 base as an isolated RL effect. The requested pilot stop rule halts after four updates if fewer than 25% of groups have nonzero return variance. Additional qualification and zero-win checks in LEARNABILITY.md are proposals requiring approval.

All pilot and main groups contain eight games from one start state. Phase 3 starts with pilot A only after approval. At its gate, offer Option S (A: 3 seeds, B: 2) and Option U (A: 2, B: 1) with updates that fit the remaining budget, informed by measured learning speed. A visible learning curve takes priority over extra seeds. The old four-game training schedules are historical proposals, not authorization.

EIG is measured, never rewarded. Audit early guesses, singleton search, large name lists, invalid behavior, and parser exploits in the pilot before main training. Legal enumeration is a result; do not silently ban it. The primary-model output cap is 2048, large enough for the measured half-candidate lists.

Reuse the pinned cookbook environment interfaces, rollout, renderer, and training plumbing at the paid implementation phases. Verify native-tokenizer parity, guard every SDK operation, and implement group-standardized advantages explicitly. Phase 1 has no Tinker adapter and made zero service calls.

Keep prose factual. This is a side project for GitHub and X. PRIOR_WORK.md is context. Do not make priority claims about the research. Distinguish forecasts from actual bills, visible reasoning from internal computation, and public model listings from authenticated availability. Report every seed, missing cell, failure, and limitation.
