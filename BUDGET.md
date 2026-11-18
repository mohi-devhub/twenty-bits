# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. That approval is unchanged in ledger.json. At the completed A11 gate, project usage is **$11.015850**, unresolved holds are **$0.467534**, and **$38.516616 remains**. These are recorded token-usage charges at the saved provider rates, not reconciled invoices.

**A11 is complete and stopped.** The stage used **$4.389417**, with **$0.104721 held**, versus $10.245707 before margin or $15.368560 with margin. Sampling cost $0.270359 for training, $0.017684 for development, $1.199043 for the matched raw control and $0.764246 for the endpoint; gradients cost $2.138085. All accepted results are collected. Native checkpoint and export holds total $0.100000; the two unavailable original turns retain $0.004721 after their exact replacements completed. Original outputs remain permanently excluded. [Current gate](MAIN_A11_GATE.md), [usage and token counts](results/main_A11/summary.json), [resume audit](research/main_A11_resume_audit.json).

| Outstanding exposure | USD held |
| --- | ---: |
| Five historical Phase 2 originals | 0.007195 |
| Four historical probe originals | 0.005618 |
| Two main A11 originals | 0.004721 |
| Two SFT checkpoint/export operations | 0.100000 |
| Five pilot checkpoint/export operations | 0.250000 |
| Two main A11 checkpoint/export operations | 0.100000 |
| Total | **0.467534** |

Lost-original exposure is **$0.017534**, below the standing rule's strict $0.50 limit; storage holds are separate. All holds remain until billing resolves them, even after hosted TTL expiry. The main adapter is saved locally with hashes. A23, B41 and hard mode have not started.

The unchanged remainder of U forecasts **$17.634728 before margin**, or **$26.452092 with 1.5x margin** (round upward to **$26.46**). It covers A23 and B41 at 30 updates and 240 games each, 64 development games per seed, two endpoint evaluations, 40 hard-mode games and storage/reupload allowances. It fits the $38.516616 available, leaving about $12.06 beyond that margin. The [measured-cost forecast](research/main_A11_remaining_forecast.json) gives training no cache credit and uses original floors plus observed mean/upper-quartile costs. B behavior remains unmeasured. **No continuation is authorized before the user decides at the A11 gate.**

Five Phase 2 originals hold $0.007195. Four probe originals hold $0.005618 after expired or unavailable responses. Their outputs are permanently excluded. The user approved exact replacements for both incidents. The probe's usage plus its unresolved holds is $0.075181 against its separate $1.50 limit. Original amounts and states remain unchanged until billing resolves them.

The alias probe used $0.082031 against its $0.25 cap including holds, with no unresolved alias-probe calls. The conditionally approved SFT and qualification used $0.370867 and retain $0.100000 for two completed checkpoint operations with bounded storage costs. Their combined $0.470867 is below the conservative $2.51 cap including holds. SFT gradient usage was $0.364010 and qualification sampling was $0.006857. SFT is dropped from the main plan because it lowered EIG. The reference model has no future allocation.

The Phase 2 forecast was $2.95805922, or $4.437088830 with margin. Its token-capped uncached envelope was $17.647606. Every paid call reserved the larger of its estimate times 1.5 and its full declared maximum before I/O. The reservation, dispatch, settlement, and 408 rules in twenty_bits/budget.py are unchanged apart from the explicitly approved $50 cap and matching validation messages.

The completed [pilot gate](PILOT_GATE.md) used **$0.291204**, with **$0.250000 held** for four native checkpoints and one external export. Combined pilot exposure is **$0.541204**, below the approved $2.00 ceiling and the $1.564452 forecast including margin. All pilot futures were collected and the final adapter downloaded with hashes; storage costs remain unknown. Hosted TTLs do not justify releasing holds.

The paired candidate-set slices cost $0.009990 (SFT) and $0.009553 (raw base), with no new holds. Their usage journals and all earlier attempts remain intact. [Pilot usage](results/pilot_A/usage.jsonl) adds sampling and guarded training mutations. One local SDK argument-binding rejection was proven unsubmitted and settled at $0; no accepted training work was retried. Pending work keeps its hold; a retrieve_future 408 re-polls the same request ID. Sampling and training IDs are durable before HTTP dispatch. After a connection drop, pause submissions, drain HTTP operations, reconnect and collect every recoverable saved future before new mutations.

[Main options priced from the pilot](research/main_options_after_pilot.json) forecast **$42.89 for S** or **$42.49 for U**, including margin, checks, endpoint evaluations, matched raw control, hard mode and holds. The user chose U (A:2/B:1, 30 updates each), with a mandatory gate after A11. A11 resumed after the historical pause and is now complete. The initial A11-stage forecast was $15.368560 with margin. The remainder waits for the user gate decision. [Replacement policy](research/replacement_policy.json) allows one exact sampling replacement below $0.50 aggregate unresolved lost-original holds, with original holds/exclusions retained. That lost-original total is $0.017534; storage holds are separate.

[PAID_PLANS.md](PAID_PLANS.md) records the approval and preserves the superseded Phase 1 proposals. The earlier 32-update, five-seed schedule no longer fits after doubling group size. Historical cost_projection.json and twenty_bits/costs.py use the earlier 40-cell grid and are not current plans.
