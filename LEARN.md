# Learning notes

## Phase 0: check the experiment before spending

We built a research record, a cost estimator, and a budget ledger. We have not built the game or contacted the Tinker service. This separation lets us find contradictions before paying for model outputs.

Previous work already teaches language models to play 20 Questions and ask informative questions. Our useful question is narrower: if the reward pays for success and charges for questions, does good information seeking emerge? In the planned reward, information gain is a measurement only. We deliberately do not reward it. Otherwise, seeing it rise would partly confirm the objective we explicitly optimized.

`twenty_bits/costs.py` estimates what the proposed workload would cost using a saved public rate card. The expensive part is repeated context. Every turn sends the candidate table and conversation again. Counting only the short YES/NO replies or model outputs would miss most of the expected cost. The assumptions are visible so we can replace them with actual token counts before a paid run.

`twenty_bits/budget.py` controls the money. A reservation sets money aside before a request is submitted. For a $1 estimate, it holds at least $1.50. If the token caps permit a higher charge, it holds that higher maximum instead. New work must fit alongside both money already spent and money held for work still running. Decimal strings avoid floating-point mistakes around the $30 boundary.

The ledger writes the reservation and dispatch state before calling the provider. If the program crashes or a response times out, the hold stays. A 408 from `retrieve_future` means to keep checking the same request ID, not to submit the job again. We only release the hold after the actual cost is known. The tests use fake calls and temporary ledgers, including competing processes, so testing the budget itself costs nothing.

Two mathematical details affect how we will interpret results. Ten percent answer noise lowers the best possible expected gain to about 0.531 bits per question. Also, `log2(N)/questions` among wins can exceed one through lucky guesses. Exact expected information gain over all questions is the cleaner score.

The cookbook already supplies multi-turn rollout and training machinery. We will adapt its environment interface to use a table and parser rather than pay another model to answer. Its current group advantages are mean-centered, so the requested standard-deviation normalization needs an explicit adapter when we reach RL.

## Phase 1: make the search problem exact

We built the table worlds, a small Boolean parser, and a game loop that never asks another model to judge an answer. The parser creates a tree and evaluates it against every row. It cannot execute Python. Flat name lists use an iterative evaluation stack, so a long legal predicate cannot exhaust Python's recursion limit.

The semantic tables contain named profiles, such as animal kind plus age and sex. They have 400 animal rows and 320 rows in each other semantic domain, but fewer underlying types. We record that limitation rather than treating every profile as an independent species or ingredient. The synthetic table has random bits and receives fresh opaque names and column order in each game. Training has a dedicated function that can sample only the fixed 200-row animals pool.

The posterior is a probability for each candidate. A truthful answer removes impossible rows. A noisy answer lowers their probability but does not make them impossible. Expected information gain averages the two possible observed answers, including lies. The game stores this measurement separately from the reward. Training still gets only wins, question cost, and invalid penalties.

Random and greedy policies give us executable references before any model call. The reported sweeps contain 24,000 games across the full grid and another 6,000 on the exact frozen paid games. Bootstrap intervals resample games, not individual questions from the same game. A repeated question after a low-probability reply is logged, but those events are rare for an efficient Bayesian player.

The table prompt lists only true column codes and maps them to attribute names. This is much shorter for sparse semantic rows than printing every zero. The table stays at the beginning of the conversation so a sampler can cache it. Real tokenizers price that repeated context; caching gets no credit in the paid forecasts until actual hits are observed.

The replay is a view of saved state. Both panels read the same target and their own logged posterior after each action. The animation clock changes which saved turn is shown; it does not simulate answers. That lets us reuse it for base and trained models without rewriting the game logic. Thinking is disabled in the proposed Qwen runs, so a later zero-reasoning chart will reflect that setting, not a discovery about internal computation.

## Phase 2: see what the base models actually do

We connected the exact game to the cookbook's environment and rollout interfaces, then played 280 Qwen games and 20 reference games. No model was trained. All questions, answers, posteriors, and token counts are saved, so we can replay the games without paying again. The adapter checked that its prompt token IDs matched the native tokenizer before sending them.

The base model did not win. All 447 valid Qwen questions used item equalities, and 311 gave zero expected information. Many other questions were invalid or too long. This is why a valid question is not automatically a useful question, and why we measure bits alongside wins and format errors. A repeated uninformative predicate can also look like a re-check without helping search.

The real output was much longer than the 64-token forecast: about 1,303 generated tokens per call on noiseless animals at N=32. Caching helped, but recorded usage still cost $5.793225. The approved cap is now $50. Five uncertain originals remain labeled orphaned, possibly billed, with $0.007195 held; their outputs are excluded permanently. The approved replacements used the same inputs and seeds.

A request is more than an HTTP call. The sampler ID and sequence number let us write its future ID to disk before sending. We verify the returned ID and keep polling it after a 408. A wire mismatch with the stock SDK's backpressure header caused the initial failures. Shutdown now lets active requests finish and saves their results before stopping.

Bootstrap intervals resample whole games. With zero wins, that bootstrap gives a zero-width interval, so we also report Wilson bounds rather than imply that the population win rate is known to be zero. Thinking was disabled for Qwen; zero visible reasoning tokens reflects that setting. The next step is an A-only pilot with groups of eight, after approval. Its reward still contains only wins, question cost, and invalid penalties. EIG stays a measurement.

## Learnability diagnosis and prompt probe

Valid syntax and useful questions are separate. The saved base games mostly repeated malformed expressions, table codes, or name lists that revealed nothing. Long outputs also returned as history on later turns, which explains the cost miss. The probe added random grammar examples and clearer wording. It won one N=8 game with a real singleton, but only 22.2% of N=8 turns and 9.9% of N=16 turns were valid. We stopped before training.

Random valid single-attribute play wins 89.7% at N=4 and 76.3% at N=8 under the declared final-guess rule. Smaller games can supply wins once syntax works. A group's returns can still vary through question costs when every game loses, so reward variance alone does not prove a useful win signal. The proposed format warm start teaches grammar, table tracking, and when to guess. It chooses no question for information gain. Its synthetic toy data would change how we describe later synthetic transfer, and it still needs approval.

A future ID does not preserve a result forever. Network failures left three probe responses expired and another unavailable. The user approved exact replacements while keeping their cost holds. Recovery now recreates the client and collects all recoverable saved futures before sending new work. A 408 keeps the same request and hold. [LEARNABILITY.md](LEARNABILITY.md) records the measured latency, proposed checks, and revised budget.

## Attribute codes and format SFT

The table already showed short column codes, so accepting those codes as exact aliases removed an unnecessary mismatch. One shared function now creates both the header and parser mapping. Names after `item ==` still mean items. Historical results keep their original grammar, and frozen game files and prompt hashes do not change.

The alias probe reached 72.6% valid turns, below the agreed 80% trigger. That activated the user's conditional format SFT approval. We trained only the current assistant action on random-question toy games. Training loss fell and qualification reached 92.0% valid turns, but only 3/32 games won. Seventeen guesses named candidates already ruled out by answers. The greedy script won all 32 of those cases. Valid grammar and informative questions are not enough if the final guess ignores the evidence.

This warm start uses cross-entropy, not RL. It introduces an attribute-question prior and exposure to random-table tasks, so future strategy and transfer claims need that disclosure and a warm-start control. The adapter is saved locally. Qualification missed its win requirement, so we stopped before RL. [ALIAS_GATE.md](ALIAS_GATE.md) records the numbers, holds, and next decision.

## Supplying the candidate set

We now give the model the remaining names after each answer. Noiseless lists are exact. Noisy lists use a fixed probability threshold plus the top candidate; names can reappear. The table and old lists stay in the conversation, so a shorter new list does not make the whole prompt shorter. We measured those native token sequences and saved new hashes alongside the old frozen hashes.

Both policies qualified: raw base won 23/32 and format SFT won 14/32. Neither guessed an eliminated item or guessed wrongly at singleton. Repeated uninformative questions and failing to guess at the budget remain useful RL targets. The SFT checkpoint was reused without more training; on this slice its random-attribute prior did not help. Raw base is the recommended pilot initialization, pending approval.

This changes what the project can claim: the main task tests question selection given state, while no-list state tracking is a small evaluation-only hard mode. EIG is still measured, never rewarded. The priced pilot has groups of eight and the unchanged four-update variance stop rule. No RL ran. [CANDIDATE_GATE.md](CANDIDATE_GATE.md) records the qualification and proposal.

## Raw-base outcome-only RL pilot

We trained a fresh Qwen3-8B LoRA adapter for 16 updates. The user chose raw base because random-question SFT lowered EIG; none of that adapter entered this policy. Each update sampled eight games on the same table and target. A game's win reward, question cost and invalid penalties became its return. We subtracted the group's average return and divided by its standard deviation, so better outcomes within that group reinforced the generated action tokens. Table and environment tokens received no direct prediction loss. EIG stayed a measurement, never a reward.

The four-update variance check passed, but variance needs interpretation: two later groups had no wins and differed only in question costs. On eight fixed development cases, wins rose from 4 to 7 and EIG from 0.483 to 0.617, mainly through fewer wasted questions. The paired interval still includes zero change. There was no name enumeration, yet five final guesses had multiple candidates left and four happened to win. Faster winning games alone would hide that risk.

The runner saves training request IDs before dispatch, just as sampling does. One unsupported SDK keyword failed locally before sending a gradient; it was settled at zero and fixed with a production-adapter regression test. Saved games were reused. All later futures were collected and the final adapter downloaded. [PILOT_GATE.md](PILOT_GATE.md) contains every update, uncertainty and cost; main runs wait for the user's choice between more seeds and more updates.

## Main setup and a safe pause

The user chose U and added a gate after A seed 11. Its frozen curriculum reaches N=32 and N=128. We added a measurement of guesses with 1, 2, 3 or 4+ candidates remaining, including wins in each bin. In noisy games the displayed list is approximate, so the log also keeps full posterior support. The reward and prompts did not change.

The Mac slept during the raw-control evaluation. We saved 52 complete games and 625 results; two unavailable requests kept their holds and were excluded. No main training update ran, so there is no partial optimizer state to repair. At the user's request we archived the journals and counters, added a guard that stops before service access, and paused at update 0. PAUSED.md records spending and the exact resume point. The standing replacement permission is saved, but no replacement will run before explicit resume.
