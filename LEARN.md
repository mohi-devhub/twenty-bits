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
