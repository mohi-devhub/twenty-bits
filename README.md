# Twenty Bits

Can outcome-based RL teach a small LLM to ask efficient yes/no questions, recover from lies, and transfer its search strategy?

Phase 0 is complete. There are no trained models or measured game results yet. **Total Tinker spend: $0.00 of $30.00**, recorded in [ledger.json](ledger.json).

The requested evaluation schedule exceeds the current budget estimate. [BUDGET.md](BUDGET.md) gives per-phase estimates and an unapproved smaller diagnostic. No evaluation counts, rewards, or caps have been changed.

Read [PRIOR_WORK.md](PRIOR_WORK.md) for related research, [TINKER_CHECK.md](TINKER_CHECK.md) for cookbook reuse and the current published model inventory, and [DESIGN_NOTES.md](DESIGN_NOTES.md) for the decisions needed before building the worlds. [LEARN.md](LEARN.md) explains the code in plain language. [PHASE0.md](PHASE0.md) is the gate report.

Run the local checks with Python 3.11 or later on macOS or Linux. No packages, account credentials, or network are needed:

```bash
python3 -m unittest discover -s tests -v
python3 -m twenty_bits.budget status
python3 -m twenty_bits.costs
```

The [source snapshot metadata](research/platform_snapshot.json) records the checked upstream revisions and rate-card hash. The ledger guard uses a process lock and atomic file replacement. Future Tinker operations must go through it.

Next is Phase 1, offline environment and baselines, after the user resumes the project and resolves the world-size choice. Work stops at every phase gate. The final README will include the measured headline chart, complete reproduction commands, and reconciled total spend once those artifacts exist.
