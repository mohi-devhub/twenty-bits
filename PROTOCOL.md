# Experiment protocol

Option U is approved on 2026-11-18, with a mandatory stop after main A seed 11's 30 updates and endpoint evaluation, before either other seed. experiments/main_A11.json freezes this stage. Its curriculum reaches N=32 at updates 16–22 and N=128 at 27–30, matching frozen animal cells. Reward, output/context/question caps, grammar, prompts and frozen games stay unchanged.

The additional guess-with-k-v1 metric uses public state just before GUESS. Noiseless k is exact consistent support; noisy k is the existing threshold-plus-MAP displayed list, with full positive support recorded separately. Report counts and wins in bins 1,2,3,4+ with all-game and guess denominators at each update/check and for raw versus endpoint frozen evals. This adds no feedback or reward.

The main condition is **candidate set provided**, approved on 2026-11-18. The research question concerns question selection given environment-computed state. It no longer tests whether the policy can maintain that state from the full answer history. `candidate-set-v1` adds only the state-feedback contract and lists to the existing grammar-example prompt. The no-list grammar-example format is evaluation-only hard mode. The user approved raw-base Qwen3-8B for the A pilot, with no SFT: random-question SFT lowered paired pooled EIG by 0.1444 bits/question and won 14/32 versus raw base 23/32. Historical SFT remains diagnostic data; none of its weights enter the main policy.

After every question answer, including INVALID, noiseless games append the exact consistent candidate list in original TABLE order. Noisy games append candidates with posterior probability **strictly greater than 0.001**, plus the MAP candidate, and explicitly identify that top candidate. MAP ties use TABLE order. This absolute threshold is fixed across domains, sizes and turns and is below the uniform prior probability at every planned N. Noisy candidates may leave and re-enter the list. The noisy list does not certify elimination or certainty. No probability values, target identity or hidden flip outcomes are supplied. Feedback uses only the public table, answers and declared noise probability.

The complete original table and every prior list remain in the conversation. A new noiseless list can shrink while the full conversation grows. Guesses and predicates may still reference any item in the original table; the list imposes no new action restriction. Rewards, original-N question budgets, grammar, aliases, output/context caps, answer/noise seeds and exact scoring are unchanged. EIG and answers use the full posterior/table, never a posterior renormalized over the displayed noisy list. The stable system prefix is shared across turns and noise modes.

Frozen targets, subsets, seeds and file hashes remain unchanged. New native-token prompt hashes are saved in `evals/candidate_set/prompt_hashes.json`; `evals/frozen/prompt_hashes.json` preserves the old Phase 2 hashes. The new manifest also records no-list hard-mode hashes. Dynamic prompt signatures and native-token parity are verified at every sampled turn. `evals/hard_mode.json` fixes two games per frozen cell for raw-base versus final-model evaluation at the end; those 40 sampling games are in approved Option U but deferred past the A11 gate. No RL will train on hard mode.

The approved attribute-code grammar is `attribute-codes-v2`. Attribute codes are exact, case-sensitive aliases for the full names in that game's header. Codes and full names can mix within one predicate. Item names after `item ==` remain literal item names, not attribute aliases. The table's lowercase codes such as `not` differ from uppercase operators such as `NOT`. A bare `item` is an attribute only when the header supplies that code; `item == <name>` remains an item equality. Ambiguous headers whose code conflicts with another full name are rejected. Historical Phase 2 and prompt-probe scores retain `names-v1`; do not rescore their trajectories under changed answers. The alias-only gate kept prompt text unchanged; the candidate-set amendment above introduces a separately versioned rendering. The reference model is dropped from future plans.

The historical learnability probe is documented in LEARNABILITY.md. It uses animals training-pool N=8 and 16 with a separately hashed prompt and random grammar examples. The later alias probe and conditional format SFT are documented in ALIAS_GATE.md. No-list SFT qualification failed on wins; after candidate feedback, raw base outperformed SFT in CANDIDATE_GATE.md. The subsequent raw-base RL pilot is documented in PILOT_GATE.md. Any adopted observation, prompt or initialization change needs matched controls before an RL comparison.

The original protocol was fixed before paid evaluation. The user approved Phase 2 on 2026-11-18: indices 0 through 27 in all ten primary cells and five games in each of four N=32 reference cells. evals/phase2.json preserves those historical models, output caps, prompts, grammar and sampling settings. The alias amendment above applies to future evaluation without changing the frozen games. The approved pilot is complete; Option U begins with A seed 11 and stops at its endpoint gate.

## Game and observations

The policy sees the domain, rules, candidate names, and the complete public table. Sparse rows list the codes of true attributes; omitted codes are false. The header maps each code to its full attribute name. Questions may use either exact full names or exact header codes under `attribute-codes-v2`. The table and rules occupy the system-message prefix; noise settings, answers and candidate feedback follow it. The target and numeric posterior values never enter the public prompt.

The initial prior is uniform over candidates. Ask with `ASK: <expr>`. Operators are uppercase AND, OR, NOT, parentheses, and `item == <name>`. NOT binds tighter than AND, which binds tighter than OR. Quoted names use JSON double quotes. Unknown attributes or item names are invalid. No Python execution is involved. Parser limits are 32,768 characters, 4,096 lexical tokens, and 64 levels of syntactic nesting. Flat name lists are evaluated iteratively and remain legal.

Outer whitespace is ignored, while additional non-empty lines are invalid. Raw action text remains logged for token accounting. Named-item counts count distinct names, so repeating one name is not treated as a large list.

Guess with `GUESS: <exact item name>`. A correct guess wins; a wrong or unknown guess ends in a loss. Malformed ASK output returns INVALID and consumes a question. Every question costs 0.03 reward; INVALID adds a 0.1 penalty. A win adds 1. There is no information reward.

The question limit is `2*ceil(log2(N))`. The last allowed question receives its answer, followed by one final-guess opportunity. Any further question or malformed action at that opportunity ends in a loss and does not exceed the question counter. A zero-question correct guess is a win, but its win-conditioned bits/question ratio is undefined. Losses and invalid questions remain in the EIG summary.

Noise independently flips each valid answer with p=0.10. Each game has a seeded flip schedule indexed by question number, shared by compared policies. An invalid question consumes its scheduled position without revealing a binary answer. GUESS is scored against the target and is never flipped.

## Exact measurements

Posterior updates multiply each candidate by its observed-answer likelihood, p or 1-p, then normalize. At p=0 zeros define the consistent set. At p=0.10 all prior-positive candidates retain positive mass.

Expected information gain is `h2(p + (1-2p)*q) - h2(p)`, where q is the current posterior mass on which the predicate is true. The noiseless ceiling is 1 bit and the noisy ceiling is 0.5310044064 bits. Realized entropy changes may be negative and are not clipped. INVALID has zero EIG.

Cell EIG is the sum of question EIG divided by questions across all games, including losses. Report win rate, mean questions among wins, invalid rate, enumeration rate, predicate tokens, and the win-conditioned `log2(N)/questions` ratio separately. Predicate length uses the pinned Qwen3-8B tokenizer for all offline policies; grammar-token counts are also available. Model outputs later log their native reasoning and action token spans separately.

Enumeration means an expression contains at least one item equality. Singleton and large-name-list counts support the audit. No name-list form is banned. A measured half-list at synthetic N=256 uses 1,409 Qwen tokens, which fits the approved primary-model 2,048-token universal output cap. Thinking is disabled for the Qwen policies. Historical Phase 1 plans assumed 64 output tokens per turn; current main forecasts use measured pilot lengths with full-cap hard-mode allowances. Unusually long outputs consume the budget faster.

An unlikely answer has predictive probability strictly below 0.20 under the pre-answer exact posterior. A re-ask is a question with the same truth vector as any previous question, or its complement. Report re-asks on the next action after an unlikely answer, divided by all such next-action opportunities, including guesses. This narrow measurement does not capture every error-correcting strategy. A new informative split can cross-check a hypothesis without repeating a truth vector.

## Baselines

Random samples an available single attribute uniformly with replacement. Greedy single-attribute maximizes exact EIG over those attributes. Greedy predicate covers every split from up to two attributes with AND, OR, and NOT, using complement equivalence to avoid duplicate scoring. Its noisy confirmation rule immediately repeats the previous valid question after an unlikely reply when posterior confidence remains below 0.95.

All policies guess a MAP candidate when noiseless posterior support has one item, noisy top posterior reaches 0.95, or the question budget ends. Ties use stable candidate or expression order. Random and greedy-single use the same noisy stopping threshold, so they can finish despite every posterior remaining positive. Their questions are always grammar-valid. These are heuristic references. The unrestricted grammar admits balanced name-membership questions, so greedy two-attribute search is not an upper bound on a learned policy.

The full offline grid has four domains, five sizes, two noise levels, 200 games per cell, and three policies: 24,000 completed games. The policies share each start state. Cell CIs resample 200 complete games 2,000 times. Undefined quantities stay null, including re-ask rate with no opportunities.

## Frozen paid bank and training boundary

The bank has 200 games in each of ten cells. Animals uses N=32 and 128; relabeled synthetic uses N=32, 128, and 256. Both noise levels appear for every domain-size pair. File hashes and world hashes are in evals/frozen/manifest.json. Public prompt hashes are frozen separately. A plan uses the same declared index slice for the base and every trained checkpoint.

RL training accepts animals only, from the fixed 200-row pool, at N=4,8,16,32,64,128, with candidate feedback enabled. Paid animals candidates come from the disjoint 200 held-out rows. Tools, foods, saved synthetic worlds, and every frozen game are excluded from RL training. The historical format warm start used procedural toy tables but its weights are excluded from the raw-base pilot and proposed main runs. Pilot development games use a separate namespace, never enter gradients and are never counted as confirmatory evaluation. Checkpoint choice does not depend on frozen test scores: keep the scheduled endpoint for each seed.

The approved policy cap is 2,048 generated tokens per turn, with thinking disabled and a 32K context window. If a rendered prompt plus allowed output cannot fit, log a context-limit loss before any service submission; never truncate the table. Output truncation is logged even when a complete legal action is recoverable. The retired gpt-oss reference used a limited 512-token slice including reasoning; its historical truncation rate must accompany any result.

The native HF tokenizer revisions and chat templates are measured offline. The cookbook adapter checks token parity before paid sampling. Sampling settings are fixed in each approved configuration. Any change to the experiment after a run begins requires stopping at a gate.

## Completed raw-base pilot

experiments/pilot_A.json fixes one group of eight games per update, 16 A updates with curriculum 4/8/4 at N=4/8/16, and eight fixed training-pool development cases at updates 0/4/8/12/16. Rank-32 LoRA starts from raw base, with learning rate 4e-5 and cookbook Adam defaults. Group advantages are (return - group mean)/(population standard deviation + 1e-8); numerically constant returns receive zero advantage. Only generated tokens receive direct prediction loss. One importance-sampling forward/backward and optimizer step runs per group, including zero-advantage groups; there is no information reward, KL penalty or extra loss. After four updates, halt if fewer than 25% of groups have nonzero return variance. The recorded 3/4 passed. Cost-only variance is separately audited.

experiments/pilot_A_games.json freezes training groups, eight development cases and two example selections. The final scheduled checkpoint is reported. No frozen-test, noisy or transfer model evaluation ran in this pilot. PILOT_GATE.md records results and the local SDK correction before any gradient dispatch. research/main_options_after_pilot.json preserves the historical S/U proposals; research/main_U_approval.json records the later U choice and the mandatory A11 gate.
