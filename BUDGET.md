# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. The approval is recorded in ledger.json. Project usage is **$5.862788**, unresolved holds are **$0.012813**, and **$44.124399 remains**. Phase 2 contributed $5.793225 and the approved prompt probe contributed $0.069563. Invoice reconciliation remains pending.

Five Phase 2 originals hold $0.007195. Four probe originals hold $0.005618 after expired or unavailable responses. Their outputs are permanently excluded. The user approved exact replacements for both incidents. The probe's usage plus its unresolved holds is $0.075181 against its separate $1.50 limit. Original amounts and states remain unchanged until billing resolves them.

The Phase 2 forecast was $2.95805922, or $4.437088830 with margin. Its token-capped uncached envelope was $17.647606. Every paid call reserved the larger of its estimate times 1.5 and its full declared maximum before I/O. The reservation, dispatch, settlement, and 408 rules in twenty_bits/budget.py are unchanged apart from the explicitly approved $50 cap and matching validation messages.

The current gate is [LEARNABILITY.md](LEARNABILITY.md), with the [Phase 2 diagnosis](DIAGNOSIS.md). [Phase 2 usage evidence](results/phase2/usage.jsonl) and [probe usage evidence](results/learnability_probe/usage.jsonl) are saved. Pending work keeps its hold; a retrieve_future 408 re-polls the same request ID. New sampling IDs are durable before HTTP dispatch. After a connection drop, reconnect and collect every recoverable saved future before new sampling.

The proposed format warm start and condition A pilot with groups of eight still need approval. [Revised forecasts](research/learnability_forecast.json) use the completed prompt probe, include 1.5x margin and storage, and replace the historical pilot_after_phase2.json proposal. Option S and Option U will be priced after measuring pilot learning speed. No training or main schedule is active.

[PAID_PLANS.md](PAID_PLANS.md) records the approval and preserves the superseded Phase 1 proposals. The earlier 32-update, five-seed schedule no longer fits after doubling group size. Historical cost_projection.json and twenty_bits/costs.py use the earlier 40-cell grid and are not current plans.
