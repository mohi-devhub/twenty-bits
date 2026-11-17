# Current budget

The ledger cap is **$30**, actual Tinker spend is **$0.00**, and outstanding holds are **$0.00**. Phase 1 made no Tinker service calls. The ledger and its guard code remain byte-for-byte unchanged from Phase 0.

[PAID_PLANS.md](PAID_PLANS.md) replaces the earlier workload estimate with two measured-token proposals. Plan 30 forecasts $19.52 before margin and $29.28 with 1.5 times margin. Plan 50 forecasts $32.34 and $48.51. Neither plan is active. The user must approve one before any service operation, and a $50 cap is not authorized yet.

The complete assumptions, per-phase totals, model alternatives, reference slice, and precision estimates are in that plan document and research/paid_plans.json. The arithmetic uses measured public prompts, full question budgets, no caching credit, and explicit output-length assumptions. Long outputs can consume the allowance faster. The current estimates do not replace a token-bounded per-call reservation.

`twenty_bits/budget.py` continues to require settled costs plus outstanding holds plus a new reservation to stay within the cap. Each reservation is the larger of estimate times 1.5 and the call's declared maximum. A missing ledger, corrupt reservation, uncertain submission, or cost discrepancy must never lead to another unguarded call. Keep pending holds, persist the request ID, and re-poll that same future after a retrieve_future 408.

Run `python3 -m twenty_bits.budget status` to inspect the account-independent project ledger. It does not contact Tinker. Plan approval starts Phase 2 only. Reconcile actual usage and stop at every later gate.

The Phase 0 scenario remains reproducible from research/cost_projection.json and twenty_bits/costs.py as historical context. It uses the superseded 40-cell paid grid and is not a current run plan.
