# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. At the completed A23 gate, recorded usage is **$16.125774**, holds are **$1.640132**, and **$32.234094 remains**. These are observed-token charges at saved provider rates, pending invoice reconciliation. All HTTP work is drained. **B41 has not started; no further Tinker operation starts before the gate decision.**

A23 used **$5.109912**, with **$0.508896 in new holds**. The primary stage used $4.361613 plus $0.505576 held, compared with its $7.816614 forecast before margin or $11.724921 with 1.5x margin. The primary forecast includes training, development, the frozen endpoint and native storage; the auxiliary evaluations have separate costs below. [Gate](MAIN_A23_GATE.md), [observed token usage](results/main_A23/summary.json), [completion](results/main_A23/completion.json).

| A23 component | Recorded usage USD | New holds USD |
| --- | ---: | ---: |
| Training, development, primary endpoint | 4.361613 | 0.505576 |
| Suffix diagnostic, auxiliary only | 0.671128 | 0.003320 |
| Hard mode, raw base and A23 | 0.077171 | 0.000000 |
| Total | **5.109912** | **0.508896** |

The suffix diagnostic's usage plus holds is $0.674448, below its $1.50 ceiling. A23 total usage plus new holds is $5.618808. The pre-A23 ledger had usage $11.015862 and holds $1.131236; no older entry or approval changed.

| Outstanding exposure | USD held |
| --- | ---: |
| Five historical Phase 2 originals | 0.007195 |
| Four historical probe originals | 0.005618 |
| Two A11 originals | 0.004721 |
| Sixteen failed A11 diagnostic originals | 0.023700 |
| Twenty-two A23 primary originals | 0.062527 |
| Two A23 suffix-diagnostic originals | 0.003320 |
| SFT checkpoint/export operations | 0.100000 |
| Pilot checkpoint/export operations | 0.250000 |
| A11 checkpoint/export operations | 0.100000 |
| Deleted persistence-smoke files | 0.640002 |
| Permanent A23 training and sampler endpoints | 0.443049 |
| Total | **1.640132** |

The **51 lost originals hold $0.107081**, strictly below the standing replacement limit of $0.50. Storage is separate. Each eligible A23 lost logical sample received one exact replacement; originals remain excluded and held. No hard-mode request needed replacement. A 404 or a locally observed collection time does not establish whether work was billed or when a server result disappeared. [Replacement policy](research/replacement_policy.json) and the gate list every new case. Unknown charges stay held after file expiry or deletion.

Both A23 checkpoint types have API `expires_at: null`. Their measured combined size is 1,476,823,234 bytes, priced at **$0.1476823234 per month** under the saved paid-plan rate. The active $0.443049 reserve covers 30 days with twice measured smoke sizes and the usual 1.5x margin, including per-operation rounding. Permanent files require future storage reconciliation and another reserved period within the cap; they do not expire when that period ends. [Storage assumptions](research/native_storage_pricing.json). Both smoke files were deleted through the API after user confirmation, and Pixel Miser files were untouched. Their earlier holds are retained.

## B41 forecast, awaiting confirmation

The unchanged 30-update noisy seed forecasts **$9.089482 before margin** and **$13.634222 with 1.5x margin**, rounded upward to **$13.64**. That fits $32.234094 available and leaves about $18.60 beyond the forecast margin. It includes 240 training games, 64 new development games, the common 280-game frozen endpoint and both no-expiry native saves with 30-day storage reserves. Raw controls and hard mode are already complete; no extra diagnostic, external upload or new domain is included.

The [measured-cost forecast](research/B41_forecast_after_A23.json) uses both A seeds, uncached training costs, original floors and pooled mean/upper-quartile profiles, then applies the offline noisy/noiseless reference ratio. The endpoint gets at most 60% cache credit; its cache-free reference total is $11.155978 before an extra margin. Noisy RL behavior remains unobserved. Per-call reservations enforce the cap even if the forecast is wrong. **A forecast is not permission to start B41.**

## Historical gates and unchanged safeguards

[MAIN_A11_GATE.md](MAIN_A11_GATE.md) preserves A11's $4.389417 usage and $0.104721 holds. Its expired hosted files prevent the deferred A11 suffix and hard-mode evaluations; local adapter hashes remain an archive. Sixteen failed diagnostic requests hold $0.023700 and produced no usable game. The two persistence samples cost $0.000012 in total; test storage remains held.

The [pilot](PILOT_GATE.md) used $0.291204 plus $0.250000 holds against its $2.00 ceiling. The alias probe used $0.082031 against $0.25. Historical SFT and qualification used $0.370867 plus $0.100000 holds, below their conservative $2.51 ceiling; SFT is excluded from main policies because it lowered qualification EIG. The paired candidate-set slices cost $0.009990 for SFT and $0.009553 for raw base. The gpt-oss reference has no future allocation.

The Phase 2 forecast was $2.95805922 before margin or $4.437088830 with margin; its uncached token-cap envelope was $17.647606. [PHASE2.md](PHASE2.md) and [DIAGNOSIS.md](DIAGNOSIS.md) preserve actual usage and forecast errors. [PAID_PLANS.md](PAID_PLANS.md) retains superseded proposals; historical cost_projection.json and twenty_bits/costs.py use the older grid.

Reservation, admission, dispatch, settlement and 408 behavior remain unchanged apart from the explicitly approved $50 cap. Every SDK operation, including metadata, uses Ledger.call. Sampling and mutation IDs are saved before dispatch and receipts checked. A retrieve_future 408 retains the original request and hold. Network recovery drains HTTP and collects all recoverable saved futures before new submissions. The execution change from 16 to 2 concurrent games altered no ledger code, timeout, experiment setting or token cap.
