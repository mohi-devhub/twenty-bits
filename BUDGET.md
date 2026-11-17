# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. The approval is recorded in ledger.json. Phase 2 recorded **$5.793225** in gross token-usage charges; **$0.007195 remains held** for five originals labeled orphaned, possibly billed. Available under the cap is **$44.199580**. Invoice reconciliation remains pending. Original outputs are permanently excluded.

The Phase 2 forecast was $2.95805922, or $4.437088830 with margin. Its token-capped uncached envelope was $17.647606. Every paid call reserved the larger of its estimate times 1.5 and its full declared maximum before I/O. The reservation, dispatch, settlement, and 408 rules in twenty_bits/budget.py are unchanged apart from the explicitly approved $50 cap and matching validation messages.

The current gate is [PHASE2.md](PHASE2.md). [Per-cell actual versus forecast costs](results/phase2/summary.csv), [usage evidence](results/phase2/usage.jsonl), and [reconciliation](results/phase2/ledger_reconciliation.json) are saved. Pending work keeps its hold; a retrieve_future 408 re-polls the same request ID. New sampling IDs are durable before HTTP dispatch.

The next pilot is condition A with groups of eight and still needs approval. [Measured pilot forecasts](research/pilot_after_phase2.json) include output-length sensitivity, 1.5× margin, and checkpoint storage. Option S and Option U will be priced after measuring pilot learning speed. No training or main schedule is active.

[PAID_PLANS.md](PAID_PLANS.md) records the approval and preserves the superseded Phase 1 proposals. The earlier 32-update, five-seed schedule no longer fits after doubling group size. Historical cost_projection.json and twenty_bits/costs.py use the earlier 40-cell grid and are not current plans.
