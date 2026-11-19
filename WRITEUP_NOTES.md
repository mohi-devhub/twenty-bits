# Notes for the later write-up

## Accepted main study and visible-budget follow-up (2026-11-19)

RL improves question quality across all three seeds. No seed learns stopping reliably: A11 gambles and develops synthetic identifier errors, A23 stalls, and B41 gambles despite noisy training. Every trained seed has fewer noisy wins than raw base (A11 31/140, A23 29/140, B41 36/140 versus base 52/140). B41's noisy training does not clearly help noisy winning or re-checking; one noisy seed limits that comparison.

The primary prompt states the maximum question count but never displays the remaining budget. That observation motivates the labelled, evaluation-only visible-budget follow-up. It adds a counter on each user turn and an explicit GUESS instruction when the counter reaches zero. Primary scores and prompt hashes stay archived unchanged; any follow-up difference combines this observation amendment with the same fixed policies, rather than further learning.

## Visible-budget results (labelled follow-up, 2026-11-19)

All 840 available-policy games completed for $3.580565, against $7.845394 forecast with margin and an $8 ceiling. No training ran. A11 was skipped because its checkpoint was not persisted and external uploads are unavailable. All 264 preflight artifacts and 54,866 older ledger entries remain unchanged.

Explicit budget state removes every extra ASK at the final opportunity: raw 65→0, A23 136→0, B41 1→0. A23 no-guess endings fall 136→0 and wins rise 138→186. Raw no-guess endings fall 70→12; all 12 remaining losses exhaust context, versus five previously. B41 no-guess endings fall 1→0 and wins rise 127→156. Raw wins remain 141/280.

Gambling persists: ambiguous guesses with budget left change raw 104→89, A23 20→27, B41 202→188. A23 introduces eight such noiseless guesses, versus zero previously. B41 still makes 136/140 noisy guesses while its displayed list is ambiguous and questions remain. Calling the counter a complete stopping fix would hide that behavior.

Pooled EIG falls for every available policy: raw 0.405→0.353, A23 0.466→0.457, B41 0.540→0.491. Noisy wins change raw 52→57, A23 29→74 and B41 36→55 out of 140. The primary observation that every trained seed has fewer noisy wins than base must stay explicitly tied to the original prompt. Under visible budget, A23 exceeds base in noisy wins. The full prompt intervention can alter question choices as well as stopping, so do not attribute every extra win solely to the terminal instruction. These are fixed-policy prompt effects, not more RL. Per-cell paired CIs and complete counts are in VISIBLE_BUDGET_GATE.md.

These are observations and hypotheses to revisit, not changes to the experiment.

- Gambling: A11 frequently guesses with multiple candidates remaining at large N, including games with unused question budget. The main curriculum allocates only 32 games to N=128, compared with 88 at N=16. Limited large-N exposure is a possible cause, stated as a hypothesis; this allocation has not been manipulated, so the current data do not establish causality. Keep the curriculum and rewards unchanged for A23/B41.
- Sampler versus trainer log probabilities: A11's largest absolute generated-token gap was 2.703809 nats. Update-mean differences ranged from -0.018563 to +0.004860 nats. Native token sequences matched; the backend cause is unestablished. Disclose this diagnostic and record the same numbers for later seeds. Do not present it as a proven explanation for any behavioral result.
- The approved suffix-tolerant re-evaluation is auxiliary only. Its A23 results must be labelled alongside, never substituted for, primary scores; A11 could not be restored. New answers change later candidate feedback and model actions; this is a fresh rollout diagnostic, not post-hoc rescoring.

## A11 checkpoint availability correction

A11 suffix diagnostic and hard mode: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**. The local adapter and hashes remain an archive. Sixteen failed diagnostic requests produced no usable output and retain $0.023700 in original holds. These are excluded and will not be replaced. The same labelled suffix diagnostic and hard-mode comparison run immediately on A23's permanent native endpoint. Native no-expiry training and sampler saves are verified in a throwaway session before A23.

## A23 observations

- Seed dependence: noiseless animal EIG improves over base for both A seeds, but A23 is 0.243887 bits/question below A11 on the paired equal-size comparison. A23 preserves strong base synthetic play (84/84 noiseless wins versus base 82/84); A11 does not (49/84). Two seeds cannot establish stable training-seed uncertainty.
- Stopping: at noiseless animal N=128, A23's ambiguous-guess count falls to zero, but 23/28 games never guess and only 5/28 win. This is a different failure from A11's gambling, not evidence of reliable stopping. The sparse large-N curriculum remains a possible cause only; its allocation was unchanged and no causal test ran.
- Sampler/trainer diagnostic: A23 maximum absolute token gap is 1.621001 nats; update-mean gaps range from -0.011956 to +0.001789. A11's maximum was 2.703809. Cause remains unknown; native prompt/output tokens match and the declared importance-sampling objective uses saved rollout log probabilities. Do not treat the smaller maximum as proof of a repair.
- Enumeration: accepted item-equality/name-list predicates remain absent. The unchanged parser nevertheless rejects 142 training questions referencing candidate names, including 78 bare names and 25 lists. Audit both legal actions and malformed attempts; do not silently ban, repair or reward them.
- Auxiliary parser: primary A23 synthetic errors are four, including three code-plus-suffix hybrids. Fresh tolerant rollouts map 27 identifiers in 27 questions and leave wins at 109/168. Thirteen pairs diverge before any mapping despite matched prompt tokens and supplied parameters, so small EIG differences cannot all be assigned to parsing. The backend/restore cause is unknown.
- Hard mode: raw base and A23 both win 0/20. Candidate feedback remains necessary for the reported main task; the tiny no-list slice does not support a learned state-tracking claim. A11's deferred suffix and hard-mode evaluations remain not run because its checkpoint was unavailable.
- Operations: no-expiry native A23 training and sampler files persist and fresh clients sample them after source completion. All 24 new lost originals remain held and excluded; exact replacements completed. The disposable-ledger I/O diagnostic led only to reduced execution concurrency, with scientific settings and ledger behavior unchanged.

See MAIN_A23_GATE.md and results/main_A23/replication_summary.json for paired game and hierarchical seed/game intervals, all cell counts and the next-stage forecast. B41 has not started.

## Accepted A23 gate: observations to carry into B41

- **Same win rate, opposite failure modes.** Noiseless animal wins are 24/56 for A11 and 25/56 for A23, a one-game difference. A11 gambles: at N=128 it guesses ambiguously in 27/28 games, 26 with unused question budget. A23 stalls: it makes no ambiguous guesses there, but 23/28 games finish without guessing. Similar observed wins hide very different stopping policies.
- **A11's identifier regression does not replicate in A23.** Synthetic invalid questions are 276 versus four; noiseless synthetic wins are 49/84 versus 84/84 (raw base: 82/84). Keep both endpoints visible and avoid treating either seed as typical.
- **A23 update-23 collapse at N=64.** That eight-game group has zero wins, 67/96 invalid questions, 24 truncated turns and 6,312.75 generated tokens/game. Mean reward is -1.1975. The protocol stayed unchanged; subsequent checks and groups recover partially. Its cause is unestablished, so do not label it a causal effect of N=64 or the ledger problem.

## Budget visibility, audited without changing the prompt

All 110 A23 extra ASK inputs retain the fixed maximum and final-guess instruction in their opening history. None has a dynamic used/remaining question count or an exhaustion notice at that turn. The environment supplies candidate state, but budget tracking still requires counting played actions. This is an observation about the task, not an established cause of stalling. B41 keeps the prompt unchanged. research/BUDGET_VISIBILITY.md includes exact text and the verified token-level counts.

## Completed B41 observations

- B41 also gambles: 203/280 games guess ambiguously, with 152 wrong guesses and only one no-guess ending. All 140 noisy games guess with multiple displayed candidates. Noisy animal N=128 wins are 0/28. The small noiseless development curve improves while every N=128 training group has zero wins.
- Noisy wins are B41 36/140, A11 31/140, A23 29/140 and raw 52/140. B41 minus mean A is +0.042857 with a paired game/A-seed interval [-0.017857, 0.107143], conditional on the single B endpoint. Its noisy EIG difference is +0.030584 [0.001093, 0.053188]. Do not translate this into a general noise-training benefit or learned re-checking claim.
- Noiseless synthetic wins are B41 72/84 versus base 82/84. Its 28 synthetic invalid questions include 13 copied code=name header pairs and 15 code_suffix hybrids. The severe A11 identifier regression is absent in A23 and smaller/mixed in B41. Do not silently repair primary scores or treat conditional valid-question EIG as a repaired policy result.
- The B41 sampler/trainer maximum logprob gap is 3.802663 nats at update 26; update means range from -0.018576 to +0.002337. Native token parity and the unchanged objective are verified. Cause and behavioral impact remain unestablished.
- Ledger bookkeeping is now transactional and indexed. B41 has no lost request or replacement, and all older holds remain. The local benchmark does not establish a controlled model-throughput speedup. Both B41 native endpoint file types have no expiry; the paid stage is stopped.

## Final write-up handoff

RESULTS.md keeps the main and visible-budget findings separate, includes every seed, and ties numeric statements to saved files. The budget display identifies a practical budget-tracking fix for A23's final-ASK stalling. Gambling remains a trained-policy behavior under both observations. Its internal cause and a specific reward-term mechanism remain unestablished. The thread is an eight-post draft, with media assignments, character checks and a repository-link placeholder pending the user's URL. No experiment or posting is authorized.
