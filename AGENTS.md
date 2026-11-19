# Twenty Bits working rules — A23 gate

## Current authorization

The user accepted A23 and authorized B41 on 2026-11-19 after the offline ledger migration and prompt-budget audit. **Run only B seed 41: fresh provider base, training p=0.10, 30 unchanged updates, groups of eight, the same curriculum/reward/prompt/grammar/caps and evaluation. Save both native endpoint types with no expiry, evaluate the unchanged 280-case frozen primary slice immediately, then stop at MAIN_B41_GATE.md. No further paid work follows automatically.** research/main_B41_approval.json records this approval; experiments/main_B41.json and research/main_B41_preflight.json freeze the stage.

Both A seeds (11/23) are complete. B41 reuses the unchanged matched raw controls: 280 frozen games and eight development games. The development checks remain the same eight noiseless N=4/8 cases; B changes training answers to p=0.10 only. The curriculum remains N=4: updates 1–2; N=8: 3–4; N=16: 5–15; N=32: 16–22; N=64: 23–26; N=128: 27–30. No main variance stop is added.

Live budget state is now in ignored ledger.sqlite3 with durable SQLite transactions and append-only change records. ledger.json is the explicit, committed audit export and is stale during a run. Use Ledger.summary/status for live numbers; do not edit the database or reconstruct it from a stale export. Missing/corrupt live state fails closed. Export only after HTTP work is drained. The migration preserved all 45,033 entries and every approval/hold. At B41 entry: usage $16.125774, held $1.640132, available $32.234094. All 216 tests passed, including the original budget contracts against both backends and mocked SQLite SDK recovery. Execution parallelism returns to 16 after a zero-error local probe (87 ms maximum event-loop lag); scientific settings and 45-second HTTP timeout are unchanged.

The prompt-budget audit verified all 110 A23 post-budget ASK inputs: every history stated the fixed maximum and final-guess rule; none stated a dynamic remaining count or exhaustion notice. Do not change the prompt. research/BUDGET_VISIBILITY.md records exact text and counts.

At the B41 gate, report every update/check and cell, plus all three seeds' wins, EIG, ambiguous-guess rate, no-guess rate and early-guess wins per noiseless/noisy cell. Include B41's invalid name-reference audit and a one-line dominant failure mode per seed. Preserve the A11/A23 observations in WRITEUP_NOTES.md. Append a short plain-language section to LEARN.md and commit. This is a side project for GitHub/X; do not make research-priority claims.

Read PROTOCOL.md, PAID_PLANS.md, NUMBERS.md, PHASE2.md, MAIN_A23_GATE.md and the B41 approval/preflight before paid work.

## Budget and collection

The user approved a **$50 total cap including active holds on 2026-11-18**. Keep the approval, reservation multiplier 1.5, admission, dispatch, settlement and 408 behavior unchanged. Every Tinker operation, including metadata, passes through Ledger.call, backed by the migrated transactional store. Never run the stock cookbook recipe or bypass the guard through SDK internals. No actual bill is inferred from a forecast.

At this gate, recorded token usage is **$16.125774**, holds **$1.640132**, available **$32.234094**. Charges use observed tokens and pinned rates; invoice reconciliation is pending. Storage and lost originals remain held until billing resolves them. Do not release a hold because a file expired or was deleted.

A retrieve_future 408 means pending work. Poll the same request_id and retain its hold; never repeat sampling, forward/backward or optimizer work because retrieval times out. Save every deterministic sampling/training request ID in both journal and ledger before HTTP dispatch, then verify the receipt. On a network error, stop new submissions, drain HTTP operations, reconnect and collect every recoverable saved future before submitting new work. Do not cancel HTTP operations to restart faster or infer server deletion time from local observations.

research/replacement_policy.json permits **one exact replacement per lost logical sampling request**, using the identical prompt, seed and settings. Keep the original hold, permanently exclude its outputs, log the case and list it at the next gate. Aggregate unresolved lost-original exposure must stay strictly below $0.50; a second loss or exception needs approval. Current exposure is **$0.107081 across 51 originals**. Storage holds are separate. A mandatory gate or explicit user pause overrides replacement authorization.

The A23 primary registry has 22 cases ($0.062527 held), suffix registry 2 ($0.003320), hard registry 0. Older 27 originals hold $0.041234: five Phase2 ($0.007195), four probe ($0.005618), two A11 ($0.004721), sixteen failed A11 diagnostic attempts ($0.023700). All outputs are permanently excluded. Preserve the older incident approvals and ledger entries exactly. All accepted replacement outputs were collected.

Historical storage holds: SFT $0.10, pilot $0.25, A11 $0.10. Deleted smoke files retain $0.640002. A23's permanent endpoint pair holds$0.443049 for 30 days using twice measured sizes and the usual 1.5 margin. These are bounds, not reconciled storage bills.

## Fixed science

Each main policy starts from provider raw Qwen3-8B with **no project SFT or pilot adapter**. Random-question SFT lowered paired candidate-set EIG by 0.1444 and won 14/32 versus raw 23/32; preserve it as historical diagnostic data only. Current main-policy synthetic transfer has no toy-SFT exposure. Do not load those historical weights.

Reward is +1 win, -0.03/question, -0.1/INVALID, with no EIG shaping, KL penalty or extra loss. Groups contain eight games from one table/target, with explicit population-standardized return advantages. Zero-advantage groups still receive the declared optimizer step. Main runs have no pilot variance stop; the historical four-update pilot rule passed 3/4 groups. Do not change rewards, grammar, caps, prompts, schedules or the evaluation protocol during a run without a user decision.

The main task is question selection with supplied state. candidate-set-v1 appends exact consistent names in noiseless games, or names with posterior strictly >0.001 plus a labelled MAP candidate in noisy games. TABLE-order ties and threshold are fixed; noisy candidates may re-enter. No target, hidden flip or numeric posterior is supplied. Scoring always uses the full table/posterior, not a renormalized displayed list. No-list hard mode is evaluation-only; neither main policy trained on it.

Use training_game from twenty_bits/worlds.py for gradients: animals only, fixed 200-row training pool, N=4/8/16/32/64/128. Frozen cases, development cases, held-out rows, tools, foods and synthetic tables never enter main gradients. Paid animal rows are disjoint held-out profiles but share underlying types with training; disclose that limitation. Frozen games and old prompt hashes remain unchanged. Main/hard-mode hashes are separate in evals/candidate_set/prompt_hashes.json. Never attribute changes across observation, grammar, prompt or SFT conditions to RL.

Grammar attribute-codes-v2 accepts exact, case-sensitive table-header codes and full attribute names, mixed within predicates. Item-equality names are literal. Primary parsing never uses the suffix-tolerant variant. twenty_bits/suffix_diagnostic.py is an auxiliary-only intervention; its 168 fresh rollouts are not repaired primary scores. Never ban legal enumeration silently. The post-hoc raw-name audit also counts malformed identity attempts without accepting them or changing rewards/EIG.

Qwen3-8B uses thinking disabled, output 2048, context 32768, temperature 0.7, top_p 1, top_k -1 and the declared generation seeds. The question budget is 2*ceil(log2(N)), followed by one final-guess opportunity. Log visible reasoning separately from actions; zero visible reasoning under a disabled setting does not measure internal computation. gpt-oss-120b has no future allocation; its capped historical slice is failure data only.

guess-with-k-v1 is measurement only. Noiseless k is positive posterior support; noisy k is the >0.001 plus MAP display. Save full positive support too, because noisy display singleton is not certainty. Report guesses/wins for k=1/2/3/4+, retaining no-guess endings in all-game denominators. Measure early guesses, legal enumeration, malformed name-query attempts, long lists, repeats, invalids, truncation and post-budget asks. EIG is measured, never rewarded.

Reuse pinned cookbook environment, rollout, renderer and training interfaces. Verify native-tokenizer parity and group advantages explicitly. Preserve matched controls and the common declared frozen slice. scripts/analyze_main_A23.py and scripts/analyze_A23_replication.py replay accepted outputs only. Finished session metadata and compressed traces are archived for credential-free reproduction.

## Native persistence and execution history

The user forbids browser access. Both no-expiry smoke files were verified through SDK/API, sampled after source finish in fresh clients, cross-checked by the user as Never expiry, then deleted exactly as approved. The API returned zero remaining test checkpoints. research/native_persistence_deletion.json records this; storage holds remain. Never mutate Pixel Miser checkpoints sampler_weights/evaluation, weights/final or weights/B-best.

A23 saved native training and sampler endpoints with expires_at:null under `tinker://19a7c48f-02fe-556c-8cc5-404284b8da40:train:0/`, names weights/main-A-seed23-step-30 and sampler_weights/main-A-seed23-step-30. API sizes are 1,107,556,469 and 369,266,765 bytes. Both paths are in the ledger and gate report. Fresh auxiliary clients sampled after source finish; no external upload was used. Future approved B41 endpoints must also save both native file types with no expiry, price storage holds and immediately run every scheduled endpoint evaluation. Never rely on external re-upload. Reconcile and reserve future storage months within the project cap.

A11 suffix diagnostic and hard mode: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**. Keep its local adapter and hashes as an archive only. MAIN_A11_GATE.md preserves its primary results. A23 hard mode replaces that unavailable scheduled comparison. Do not rewrite old A11 summaries against today's ledger.

A23 execution changed 16→2 concurrent games only after draining all HTTP work, collecting every recoverable future (pending 0) and verifying 93 completed mutations. Config, seed/data order, 30 updates, model weights, scientific settings and ledger/transport code stayed unchanged. A disposable-copy diagnostic found median 8.912 seconds of synchronous guard work, dominated by JSON serialization; it can starve a 45-second HTTP collector. This is a local diagnostic, not a full speedup claim or proof that every connection error had that cause. See research/A23_execution_concurrency.json and research/A23_ledger_io_diagnostic.json. The user allowed continuing on battery; AC returned before the announced low-charge drain threshold, so no power stop occurred. Scope caffeinate to authorized runners; it cannot prevent clamshell sleep.

PAUSED.md, research/main_A11_pause.json and the paused A11 archive are historical. The user explicitly resumed A11, accepted both A gates and authorized B41 separately. Follow the current B41 approval; stop at its gate. All old holds, exclusions and hashes remain. Keep credentials, .env and adapter binaries ignored and untracked.
