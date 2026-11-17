# Main comparisons

The main study compares the base policy with scheduled endpoint checkpoints under the approved paid plan. This file records the comparisons before main training.

1. Outcome-only RL: paired change in EIG/question, win rate, and questions/win on the same frozen noiseless animal games, with N=128 reported separately.
2. Strategy: item-equality rate, singleton search, large name lists, and native predicate token length. Transfer is also stratified by enumeration behavior. A legal enumeration strategy is reported as a result.
3. Transfer: base-versus-trained changes on relabeled synthetic at N=32,128,256. The N=256 result combines domain and size transfer. Held-out animals are profiles, with shared underlying types disclosed in data/WORLDS.md.
4. Noise: condition B versus A at p=0.10 for paired win rate, EIG, and next-action re-ask rate after unlikely answers. Always report the denominator of re-ask opportunities. A zero or small denominator cannot support a strong behavioral claim.
5. Tokens: native action and visible reasoning tokens per game. With thinking disabled, zero reasoning is a protocol choice and does not show that training reduced internal computation.

Resample complete games, preserve pairing between base and trained outputs and between the two noise versions of each underlying case, and use 10,000 bootstrap draws in the paid analysis. Across training runs, resample seeds before games. Report seed-level point estimates as well as intervals. A condition with one seed has no estimate of between-seed variation. Two or three seeds still give unstable seed uncertainty; the plans show a sensitivity calculation rather than promising a tight interval.

Do not select the best seed, checkpoint, domain, or example for the headline. Pool cells with equal weight for the headline and show every cell separately. Use paired permutation tests for base-versus-trained per-game EIG as a secondary check, with the test family and all p-values reported. Treat win-only statistics as conditional and subject to survivorship effects.

The pilot audit checks early guesses, singleton enumeration, large name lists, repeated invalid actions, truncated outputs, and parser exploits before any main run. Any protocol change is a new approved run, never a silent continuation. Save failed runs and missing cells, with their reasons. The ledger supplies actual project spend, not these forecast totals.
