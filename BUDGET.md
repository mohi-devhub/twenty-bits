# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. All declared U main runs are now complete. Recorded usage is **$20.100658**, active holds **$2.083181**, and **$27.816161 remains**. Usage uses observed tokens at pinned rates, pending invoice reconciliation. **Stopped at MAIN_B41_GATE.md; no further paid work is authorized.**

Live state is in ignored `ledger.sqlite3`. The completed `ledger.json` audit export matches it. During a run, that JSON is stale; use Ledger.summary/status for live numbers. Migration preserved all 45,033 prior entries, approvals and holds. The final append-only history has 84,310 events and reconstructs 54,866 current records exactly. [Storage rules](LEDGER.md), [migration equality](research/ledger_migration.json), [event archive](research/ledger_events_archive.json).

## B41 actual versus forecast

B41 used **$3.974884**, with **$0.443049 held** for its two permanent native endpoints. Combined exposure is **$4.417933**, versus **$9.089482 forecast before margin / $13.634222 with 1.5x margin**. The stage completed 240 training games, 64 development games and all 280 endpoint games, with zero lost requests or replacements. Raw controls were reused without new charges.

| B41 component | Recorded usage USD |
| --- | ---: |
| Training sampling | 0.372437 |
| Development sampling | 0.018617 |
| Frozen endpoint sampling | 0.692172 |
| Forward/backward | 2.891658 |
| Total | **3.974884** |

Before B41, usage was $16.125774 and holds $1.640132. No older entry or approval changed. [Observed token counts](results/main_B41/summary.json), [forecast assumptions](research/B41_forecast_after_A23.json), [gate](MAIN_B41_GATE.md).

## Outstanding holds

| Exposure | USD held |
| --- | ---: |
| Five Phase 2 originals | 0.007195 |
| Four probe originals | 0.005618 |
| Two A11 originals | 0.004721 |
| Sixteen failed A11 diagnostic originals | 0.023700 |
| Twenty-two A23 primary originals | 0.062527 |
| Two A23 diagnostic originals | 0.003320 |
| SFT checkpoint/export operations | 0.100000 |
| Pilot checkpoint/export operations | 0.250000 |
| A11 checkpoint/export operations | 0.100000 |
| Deleted persistence-smoke files | 0.640002 |
| Permanent A23 endpoint pair | 0.443049 |
| Permanent B41 endpoint pair | 0.443049 |
| Total | **2.083181** |

The **51 lost originals hold $0.107081**, strictly below the standing replacement rule's $0.50 limit. Storage is separate. Those outputs remain permanently excluded, even if recovered later. All eligible replacements completed. A local 404, timeout or file deletion does not resolve billing; holds remain until reconciliation.

Both A23 and B41 native endpoint file types have API `expires_at: null`. B41's combined measured size is 1,476,823,252 bytes, priced at **$0.1476823252/month** under the saved paid-plan rate. Each pair's $0.443049 reserve covers 30 days with twice measured smoke sizes and the usual 1.5x margin, including per-operation rounding. Permanent files do not expire at the end of that reserved period; future storage requires reconciliation within the cap. [Storage assumptions](research/native_storage_pricing.json). Both smoke files were API-verified absent after approved deletion. Pixel Miser files were untouched.

## Historical gates

A23 added $5.109912 in usage and $0.508896 holds: primary $4.361613 + $0.505576 held, suffix diagnostic $0.671128 + $0.003320 held, and hard mode $0.077171. Its primary-only forecast was $7.816614 before margin / $11.724921 with margin; auxiliary work was separate. [MAIN_A23_GATE.md](MAIN_A23_GATE.md) preserves the full scope comparison.

A11 used $4.389417 plus $0.104721 held. Its expired hosted files prevented deferred suffix and hard-mode evaluation; local adapter hashes remain an archive. Sixteen failed diagnostic requests produced no usable game and hold $0.023700. The later persistence samples cost $0.000012. [MAIN_A11_GATE.md](MAIN_A11_GATE.md).

The pilot used $0.291204 plus $0.250000 held against a $2.00 ceiling. The alias probe used $0.082031 against $0.25. Historical SFT/qualification used $0.370867 plus $0.100000 held, inside $2.51; SFT was excluded from main policies because it lowered EIG. Paired candidate-set slices cost $0.009990 for SFT and $0.009553 for raw base. The gpt-oss reference has no future allocation.

Phase 2 forecast $2.95805922 before margin / $4.437088830 with margin; its uncached cap envelope was $17.647606. [PHASE2.md](PHASE2.md) and [DIAGNOSIS.md](DIAGNOSIS.md) retain the actual cost and forecasting errors. [PAID_PLANS.md](PAID_PLANS.md) preserves earlier proposals, rather than silently repricing history.

## Unchanged safeguards

Every SDK operation, including metadata, still uses Ledger.call. Reservation is at least estimated cost × 1.5 or the declared maximum, whichever is larger. Sampling and mutation IDs are durable before HTTP dispatch; receipts are checked. A retrieve_future 408 re-polls the same ID and retains its hold. Network recovery drains HTTP work and collects saved futures before new submissions. One exact sampling replacement is allowed only under the standing rule, with the original hold and exclusion retained. The migration changes storage and indexed reads, not these rules or the $50 cap.
