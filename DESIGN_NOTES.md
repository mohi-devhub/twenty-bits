# Design questions found in Phase 0

These notes identify issues before any environment or protocol is frozen. They do not change the user's requested rewards, caps, grammar, or evaluation schedule.

## N=256 needs larger worlds

A subset cannot contain 256 distinct items from a world with 200 animals or 150 tools or foods. Repeated names or duplicate attribute vectors would violate the task. Dropping constant attributes cannot fix this.

Proposal: create at least 300 distinct, unique rows per domain, while limiting animals training to a documented pool of about 200 items. Evaluate N=256 using the larger animals pool and larger held-out worlds. The animals result would then mix size transfer and some new item names; report that explicitly. Alternatively, train on the whole enlarged animals pool and call it size-only transfer. The user must choose the intended interpretation before Phase 1 generates its worlds.

Sixteen semantic attributes may not distinguish hundreds of plausible animals or tools. First count unique vectors. If too few exist, add sensible distinguishing attributes or reduce the pool with approval. Do not add arbitrary identity bits and quietly describe them as semantic traits. Synthetic rows can be regenerated until unique. Dropping columns constant within a subset preserves uniqueness if the full vectors were unique.

## Noise changes the information ceiling

Let `q` be the current posterior mass for which a predicate is true, and let `p` be the independent answer-flip probability. The probability of receiving YES is `p + (1-2p)*q`. With binary entropy `h2`, the exact expected information gain is:

`EIG = h2(p + (1-2p)*q) - h2(p)`

The derivation uses `I(target; observed_answer) = H(observed_answer) - H(observed_answer | target)`. The second term is `h2(p)` for every deterministic predicate. This also shows why expectations in noisy mode must include the answer flips, not just the noiseless true answers.

At p=0 the maximum is 1 bit. At p=0.10 it is **1 - h2(0.10) = 0.5310044064 bits**. No RL policy can reach 1 expected bit per noisy binary answer. A future chart can retain the requested 1.0 reference and also show the noise-specific ceiling. No experiment setting changes are needed to label the mathematics correctly.

For a received answer `y`, update each target probability by its answer likelihood, either `1-p` or `p`, then normalize. At p=0.10 every item with positive prior retains positive posterior after finitely many answers. A "one candidate remains" stopping rule will never fire under an exact noisy posterior. The random and single-attribute baselines therefore need a declared noisy stopping rule too, not only the greedy-predicate baseline.

The received-answer entropy change `H(before) - H(after)` can be negative on a surprising observation. Its expectation equals EIG. Do not clip negative realized changes or substitute the realized lucky split for EIG. INVALID provides no target information and must contribute zero EIG while still counting toward question cost.

## The win-only ratio is not bounded by one

Keep the requested `log2(N) / questions_used` statistic for wins, but label it as a win-conditioned ratio. A lucky singleton question can win quickly and yield a ratio above 1. A lucky guess with zero questions has an undefined ratio, not infinite information. Report zero-question wins separately and leave the ratio undefined for them.

`ceil(log2 N)` is the noiseless worst-case floor for guaranteed identification using binary answers. It is not a lower bound on every winning episode, especially with a free final guess and tolerated losses. For powers of two, `log2 N` is also the minimum average question count for a zero-error complete identification strategy over uniformly sampled targets.

EIG averaged over questions in all games is the primary efficiency measurement. Win rate and questions per win remain separate. A model that guesses early must not look efficient merely because only its lucky wins enter the ratio.

## A two-attribute greedy baseline is a reference, not an oracle

The grammar permits arbitrary disjunctions of `item == name`. A player can implement exact binary partition search without using semantic attributes. In contrast, the requested greedy-predicate baseline searches only two attributes and can miss a balanced split. Its score is not a mathematical upper bound on RL.

Proposal: keep all three requested baselines and add a noiseless balanced-membership oracle as a supplementary exact reference. Log enumerated names and predicate tokens for every policy. Do not ban legal long predicates or change the reward if they dominate. Stop and ask at the pilot audit as requested.

In noisy mode, split posterior mass rather than candidate counts. A finite discrete posterior may have no 50/50 partition, and minimizing immediate entropy need not maximize win probability under a finite question budget. Call the Bayesian greedy baseline a heuristic rather than claiming optimal play.

## Freeze details before any zero-shot evaluation

Phase 1 needs explicit choices for final-guess timing after the last allowed answer, malformed guesses, repeated questions, stopping thresholds, action extraction from reasoning, expression size and recursion protection, and tie breaking. These are required definitions, not excuses to change settings after a run starts. A parser must never call Python `eval` on model output.

The expected output count in the cost estimate is not a token cap decision. Choose a cap that includes visible reasoning and action tokens, measure longest prompts offline, and freeze it before Phase 2. Renderer-parsed reasoning and action spans should account for every generated token, with unclassified tokens reported rather than guessed away.

Prepare a separate animals development split for reward tuning, threshold selection, and checkpoint decisions. Never train on frozen evaluation games or held-out domains. If frozen evaluation results inform pilot tuning, disclose that those games are development data and reserve a sealed confirmatory subset before Phase 4. A frozen test file alone does not prevent adaptive overfitting.

For seeded answer flips, pre-generate a per-game flip stream by question index so policies share the same flip schedule on paired games. Their questions can still differ. Confirm and cross-check rates need a fixed definition of a low-probability answer and a semantic predicate equivalence check over table rows. Repetition alone is not evidence of useful error recovery.

With only three training seeds, intervals across seeds will be unstable. Phase 5 should resample seeds and paired games at their appropriate levels, preserve base-versus-trained game pairing, and avoid treating thousands of games from one checkpoint as thousands of independent training runs.

## Phase 1 resolution

These Phase 0 notes are historical context. PROTOCOL.md now records the implemented rules. The user approved larger worlds, a fixed 200-row animals training pool, a ten-cell paid bank, outcome-only rewards, and a Phase 1 replay. The semantic tables use explicit profiles and larger descriptive vocabularies; their coverage and limitations are in data/WORLDS.md. Paid scope remains unapproved until a plan is chosen.
