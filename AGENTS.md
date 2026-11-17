# Twenty Bits working rules

Phase 1 is complete. Stop until the user approves a paid plan. That approval starts Phase 2 only. Append a short plain-language section to LEARN.md and commit at the end of each phase.

The active Tinker cap remains $30. Plan 50 is a proposal and does not authorize a cap increase. Keep ledger.json, twenty_bits/budget.py, its holds, and 408 behavior unchanged unless the user explicitly approves the cap change. Every Tinker operation, including metadata operations, goes through Ledger.call. Do not run the stock cookbook recipe or bypass the guard through its internals.

A retrieve_future 408 means pending work. Re-poll the original request_id and retain its hold. Never resubmit sampling, training, or optimizer work because polling times out. Unknown costs remain held until reconciled.

Use training_game from twenty_bits/worlds.py for training. It accepts only animals, the fixed 200-row training pool, and N=16,32,64,128. Frozen games and held-out rows never enter gradients. Tools, foods, and synthetic are transfer domains. The paired paid animals games use disjoint held-out profiles, not entirely unfamiliar underlying types.

Read PROTOCOL.md, PAID_PLANS.md, NUMBERS.md, and PHASE1.md before continuing. Freeze sampling settings before paid work and do not change rewards, caps, grammar, or evaluation protocol within a run. Stop and ask if a change is necessary. Preserve the common declared frozen slice across all models and checkpoints.

EIG is measured, never rewarded. Audit early guesses, singleton search, large name lists, invalid behavior, and parser exploits in the pilot before main training. Legal enumeration is a result; do not silently ban it. The primary-model output cap proposal is 2048, large enough for the measured half-candidate lists.

Reuse the pinned cookbook environment interfaces, rollout, renderer, and training plumbing at the paid implementation phases. Verify native-tokenizer parity, guard every SDK operation, and implement group-standardized advantages explicitly. Phase 1 has no Tinker adapter and made zero service calls.

Keep prose factual. This is a side project for GitHub and X. PRIOR_WORK.md is context. Do not make priority claims about the research. Distinguish forecasts from actual bills, visible reasoning from internal computation, and public model listings from authenticated availability. Report every seed, missing cell, failure, and limitation.
