# Phase 1 protocol

The approved attribute-code grammar is now `attribute-codes-v2`. Attribute codes are exact, case-sensitive aliases for the full names in that game's header. Codes and full names can mix within one predicate. Item names after `item ==` remain literal item names, not attribute aliases. The table's lowercase codes such as `not` differ from uppercase operators such as `NOT`. A bare `item` is an attribute only when the header supplies that code; `item == <name>` remains an item equality. Ambiguous headers whose code conflicts with another full name are rejected. Historical Phase 2 and prompt-probe scores retain `names-v1`; do not rescore their trajectories under changed answers. Frozen games, hashes, rewards, budgets and public prompt text are unchanged. The reference model is dropped from future plans.

The 2026-11-18 learnability probe is a separate approved development run, documented in LEARNABILITY.md. It uses animals training-pool N=8 and 16 with a separately hashed prompt and random grammar examples. The later alias probe and conditional format SFT are documented in ALIAS_GATE.md. Qualification failed on wins, and no RL has occurred. The training factory also supports N=4 and 8 for proposed follow-up curricula. Any adopted prompt or SFT change needs matched controls before an RL comparison.

The original protocol was fixed before paid evaluation. The user approved Phase 2 on 2026-11-18: indices 0 through 27 in all ten primary cells and five games in each of four N=32 reference cells. evals/phase2.json preserves those historical models, output caps, prompts, grammar and sampling settings. The alias amendment above applies to future evaluation without changing the frozen games. RL still needs the next gate approval.

## Game and observations

The policy sees the domain, rules, candidate names, and the complete public table. Sparse rows list the codes of true attributes; omitted codes are false. The header maps each code to its full attribute name. Questions may use either exact full names or exact header codes under `attribute-codes-v2`. The table and rules occupy the system-message prefix; noise settings and conversation follow it. The target and the exact posterior never enter the public prompt.

The initial prior is uniform over candidates. Ask with `ASK: <expr>`. Operators are uppercase AND, OR, NOT, parentheses, and `item == <name>`. NOT binds tighter than AND, which binds tighter than OR. Quoted names use JSON double quotes. Unknown attributes or item names are invalid. No Python execution is involved. Parser limits are 32,768 characters, 4,096 lexical tokens, and 64 levels of syntactic nesting. Flat name lists are evaluated iteratively and remain legal.

Outer whitespace is ignored, while additional non-empty lines are invalid. Raw action text remains logged for token accounting. Named-item counts count distinct names, so repeating one name is not treated as a large list.

Guess with `GUESS: <exact item name>`. A correct guess wins; a wrong or unknown guess ends in a loss. Malformed ASK output returns INVALID and consumes a question. Every question costs 0.03 reward; INVALID adds a 0.1 penalty. A win adds 1. There is no information reward.

The question limit is `2*ceil(log2(N))`. The last allowed question receives its answer, followed by one final-guess opportunity. Any further question or malformed action at that opportunity ends in a loss and does not exceed the question counter. A zero-question correct guess is a win, but its win-conditioned bits/question ratio is undefined. Losses and invalid questions remain in the EIG summary.

Noise independently flips each valid answer with p=0.10. Each game has a seeded flip schedule indexed by question number, shared by compared policies. An invalid question consumes its scheduled position without revealing a binary answer. GUESS is scored against the target and is never flipped.

## Exact measurements

Posterior updates multiply each candidate by its observed-answer likelihood, p or 1-p, then normalize. At p=0 zeros define the consistent set. At p=0.10 all prior-positive candidates retain positive mass.

Expected information gain is `h2(p + (1-2p)*q) - h2(p)`, where q is the current posterior mass on which the predicate is true. The noiseless ceiling is 1 bit and the noisy ceiling is 0.5310044064 bits. Realized entropy changes may be negative and are not clipped. INVALID has zero EIG.

Cell EIG is the sum of question EIG divided by questions across all games, including losses. Report win rate, mean questions among wins, invalid rate, enumeration rate, predicate tokens, and the win-conditioned `log2(N)/questions` ratio separately. Predicate length uses the pinned Qwen3-8B tokenizer for all offline policies; grammar-token counts are also available. Model outputs later log their native reasoning and action token spans separately.

Enumeration means an expression contains at least one item equality. Singleton and large-name-list counts support the later audit. No name-list form is banned. A measured half-list at synthetic N=256 uses 1,409 Qwen tokens, which fits the proposed primary-model 2,048-token universal output cap. Thinking is disabled for the Qwen policies. The output forecast used in cost plans is 64 tokens, not that cap; unusually long outputs consume the budget faster.

An unlikely answer has predictive probability strictly below 0.20 under the pre-answer exact posterior. A re-ask is a question with the same truth vector as any previous question, or its complement. Report re-asks on the next action after an unlikely answer, divided by all such next-action opportunities, including guesses. This narrow measurement does not capture every error-correcting strategy. A new informative split can cross-check a hypothesis without repeating a truth vector.

## Baselines

Random samples an available single attribute uniformly with replacement. Greedy single-attribute maximizes exact EIG over those attributes. Greedy predicate covers every split from up to two attributes with AND, OR, and NOT, using complement equivalence to avoid duplicate scoring. Its noisy confirmation rule immediately repeats the previous valid question after an unlikely reply when posterior confidence remains below 0.95.

All policies guess a MAP candidate when noiseless posterior support has one item, noisy top posterior reaches 0.95, or the question budget ends. Ties use stable candidate or expression order. Random and greedy-single use the same noisy stopping threshold, so they can finish despite every posterior remaining positive. Their questions are always grammar-valid. These are heuristic references. The unrestricted grammar admits balanced name-membership questions, so greedy two-attribute search is not an upper bound on a learned policy.

The full offline grid has four domains, five sizes, two noise levels, 200 games per cell, and three policies: 24,000 completed games. The policies share each start state. Cell CIs resample 200 complete games 2,000 times. Undefined quantities stay null, including re-ask rate with no opportunities.

## Frozen paid bank and training boundary

The bank has 200 games in each of ten cells. Animals uses N=32 and 128; relabeled synthetic uses N=32, 128, and 256. Both noise levels appear for every domain-size pair. File hashes and world hashes are in evals/frozen/manifest.json. Public prompt hashes are frozen separately. A plan uses the same declared index slice for the base and every trained checkpoint.

Training accepts animals only, from the fixed 200-row pool, at N=16,32,64,128. Paid animals candidates come from the disjoint 200 held-out rows. Tools, foods, synthetic, and every frozen game are excluded from training. Pilot development games use a separate namespace and are never counted as confirmatory evaluation. Checkpoint choice does not depend on frozen test scores: keep the scheduled endpoint for each seed.

The approved policy cap is 2,048 generated tokens per turn, with thinking disabled and a 32K context window. If a rendered prompt plus allowed output cannot fit, log a context-limit loss before any service submission; never truncate the table. Output truncation is logged even when a complete legal action is recoverable. The gpt-oss reference is a limited 512-token sanity slice including reasoning, so its truncation rate must accompany any result.

The native HF tokenizer revisions and chat templates are measured offline. The Phase 2 cookbook adapter must check token parity before paid sampling. Sampling settings will be fixed in the approved Phase 2 configuration. Any change after a run begins requires stopping at a gate.
