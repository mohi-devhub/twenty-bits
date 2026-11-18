# Historical pause — resumed, then completed A11

The user explicitly resumed with AC power and an open lid. [Resume audit](research/main_A11_resume_audit.json) verified model availability, cached journals, seed, data order and budget. A11 completed all 30 updates and its endpoint evaluation on 2026-11-19. The runner has exited. [MAIN_A11_GATE.md](MAIN_A11_GATE.md) is current; wait for the next gate decision. Everything below describes the earlier pause snapshot, not the current run state.

User-requested pause on 2026-11-18. **No new requests or background collector are running. Do not resume until the user says “resume”.**

- Main A seed 11: **last completed update 0/30; next update 1**. No forward/backward or optimizer call ran. There is no partial update and no main-run checkpoint; only raw initialization exists.
- Matched raw control: **52/280 complete games**, with **625 collected results from 627 saved sampling requests**. Complete games and partial-game turn caches are preserved.
- Two original requests remain unavailable after repeated 404s; the final collection attempt returned 522 for both. Their **$0.004721 holds remain**, their outputs are permanently excluded, and **zero replacements were submitted**. IDs and signatures are in [the incident record](research/main_A11_recovery_incident.json).
- The user approved one exact replacement per lost logical request when unresolved original holds remain **below $0.50**, with identical prompt, seed and settings, retained original holds, permanent output exclusion, ledger logging and next-gate reporting. A second loss or an exception needs approval. This rule is recorded in [replacement_policy.json](research/replacement_policy.json); the current pause overrides submissions.

Recorded usage for this main stage is **$0.192932**, with **$0.004721 held**. Project usage is **$6.819365**, holds **$0.367534**, and available budget **$42.813101 / $50**. Holds comprise old lost originals $0.012813, new lost originals $0.004721, SFT storage $0.100000 and pilot storage $0.250000. Billing reconciliation remains pending.

The immutable [configuration](experiments/main_A11.json), [compressed data order](experiments/main_A11_games.json.gz), [pause state](research/main_A11_pause.json), and [hashed archive](results/main_A11/paused/manifest.json) preserve the resume point. Verification restores the ignored JSON manifest byte-for-byte when needed, checking its original hash. The archive contains all request/response journals, complete games, operation receipts and session counters. Live equivalents remain under ignored `runs/main-U-A11-v1/`. Raw initialization uses LoRA seed 11; no SFT or pilot adapter is loaded.

After explicit resume:

1. Recheck the ledger, archive hashes, session state and immutable configuration/data. Confirm a powered Mac with its lid open; scope a `caffeinate` idle-sleep assertion to the runner. Lid closure caused the recorded interruption.
2. Reconcile saved request IDs before new submissions. Activate the approved replacement-key aliases in the incident, verifying identical signatures, then resume cached turns and those two exact replacements. Retain original holds and exclusions. If hosted raw initialization expired, recreate raw initialization with seed 11; no trained optimizer state exists to lose.
3. Finish the matched 280-game control, then run updates 1–30 in the same data order. The curriculum reaches N=32 at updates 16–22 and N=128 at 27–30.
4. Keep four-update checks, the new guess-with-k metric, frozen endpoint eval and all unchanged rewards/caps. **Stop after A11's endpoint before A23 or B41.** Hard mode remains at the end.

The runner has a local pause guard that returns before SDK construction. Only explicit user resume permits clearing it. [Pause verification](results/main_A11/paused/validation.json) records checks without service calls.
