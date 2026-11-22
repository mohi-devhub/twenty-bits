# Submission costs

The approved Tinker cap is **$0.40** including any new holds. The audit, archive analyses, figures, and transcripts use no paid calls. The approved evaluation uses base Qwen3-8B on 28 frozen noiseless animal N=32 cases with added halving instructions. No learning-rate arms are part of this submission. [Gate 1 audit](docs/SUBMISSION_AUDIT.md).

| Operation | Estimated usage proxy | Forecast incl. allowance and reservation margin | Cap | Recorded usage | New holds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Free submission work | $0 | $0 | $0 | $0 | $0 |
| Halving-prompt evaluation | $0.184994115 | $0.319114848375 | $0.40 | $0.271615 | $0.000000 |

Offline rendering replayed the saved raw trajectories with the amended prompt. It added 150 input tokens per call at most and yielded an uncached proxy of $0.178072005. The padded forecast allows 256 extra input tokens on each of 308 possible calls, then applies a 1.15 trajectory allowance and the 1.5 reservation multiplier. Each sampling reservation uses the full output cap and goes through the existing $50 project guard and approved $0.40 run guard. No checkpoint storage is planned. The historical study's completed ledger and holds are archived separately. [Preflight and prompt hashes](results/submission/halving/preflight.json), [historical ledger](ledger.json), [provider rates](research/rate_recheck.json).

All 28 games completed, and all 308 sampling requests settled. The session finished and HTTP work drained. Recorded usage comes from observed tokens at pinned rates, pending invoice reconciliation. Live project usage after the run is $23.952838 with existing holds of $2.083181. The run-specific export preserves the historical study snapshot. [Completion record](results/submission/halving/completion.json), [run ledger entries](results/submission/halving/ledger_entries.jsonl.gz).
