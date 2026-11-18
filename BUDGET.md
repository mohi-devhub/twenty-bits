# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. The approval is recorded in ledger.json. Project usage is **$6.315686**, unresolved holds are **$0.112813**, and **$43.571501 remains**. Phase 2 contributed $5.793225, the prompt probe $0.069563, the alias probe $0.082031, and format SFT plus qualification $0.370867. Invoice reconciliation remains pending.

Five Phase 2 originals hold $0.007195. Four probe originals hold $0.005618 after expired or unavailable responses. Their outputs are permanently excluded. The user approved exact replacements for both incidents. The probe's usage plus its unresolved holds is $0.075181 against its separate $1.50 limit. Original amounts and states remain unchanged until billing resolves them.

The alias probe used $0.082031 against its $0.25 cap including holds, with no unresolved alias-probe calls. The conditionally approved SFT and qualification used $0.370867 and retain $0.100000 for two completed checkpoint operations with bounded storage costs. Their combined $0.470867 is below the conservative $2.51 cap including holds. SFT gradient usage was $0.364010 and qualification sampling was $0.006857. No RL ran. The reference model has no future allocation.

The Phase 2 forecast was $2.95805922, or $4.437088830 with margin. Its token-capped uncached envelope was $17.647606. Every paid call reserved the larger of its estimate times 1.5 and its full declared maximum before I/O. The reservation, dispatch, settlement, and 408 rules in twenty_bits/budget.py are unchanged apart from the explicitly approved $50 cap and matching validation messages.

The current gate is [ALIAS_GATE.md](ALIAS_GATE.md). [Phase 2](results/phase2/usage.jsonl), [prompt-probe](results/learnability_probe/usage.jsonl), [alias-probe](results/alias_probe/usage.jsonl) and [SFT](results/format_sft/usage.jsonl) usage journals are saved. Pending work keeps its hold; a retrieve_future 408 re-polls the same request ID. New sampling IDs are durable before HTTP dispatch. After a connection drop, reconnect and collect every recoverable saved future before new sampling.

Format SFT is complete. Its qualification failed the 8/32 win requirement, so no RL pilot is scheduled or approved. [Earlier forecasts](research/learnability_forecast.json) remain historical proposals. Option S and Option U wait for a learnable policy and measured pilot learning speed. No main schedule is active.

[PAID_PLANS.md](PAID_PLANS.md) records the approval and preserves the superseded Phase 1 proposals. The earlier 32-update, five-seed schedule no longer fits after doubling group size. Historical cost_projection.json and twenty_bits/costs.py use the earlier 40-cell grid and are not current plans.
