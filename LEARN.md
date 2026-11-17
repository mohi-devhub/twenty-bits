# Learning notes

## Phase 0: check the experiment before spending

We built a research record, a cost estimator, and a budget ledger. We have not built the game or contacted the Tinker service. This separation lets us find contradictions before paying for model outputs.

Previous work already teaches language models to play 20 Questions and ask informative questions. Our useful question is narrower: if the reward pays for success and charges for questions, does good information seeking emerge? In the planned reward, information gain is a measurement only. We deliberately do not reward it. Otherwise, seeing it rise would partly confirm the objective we explicitly optimized.

`twenty_bits/costs.py` estimates what the proposed workload would cost using a saved public rate card. The expensive part is repeated context. Every turn sends the candidate table and conversation again. Counting only the short YES/NO replies or model outputs would miss most of the expected cost. The assumptions are visible so we can replace them with actual token counts before a paid run.

`twenty_bits/budget.py` controls the money. A reservation sets money aside before a request is submitted. For a $1 estimate, it holds at least $1.50. If the token caps permit a higher charge, it holds that higher maximum instead. New work must fit alongside both money already spent and money held for work still running. Decimal strings avoid floating-point mistakes around the $30 boundary.

The ledger writes the reservation and dispatch state before calling the provider. If the program crashes or a response times out, the hold stays. A 408 from `retrieve_future` means to keep checking the same request ID, not to submit the job again. We only release the hold after the actual cost is known. The tests use fake calls and temporary ledgers, including competing processes, so testing the budget itself costs nothing.

Two mathematical details affect how we will interpret results. Ten percent answer noise lowers the best possible expected gain to about 0.531 bits per question. Also, `log2(N)/questions` among wins can exceed one through lucky guesses. Exact expected information gain over all questions is the cleaner score.

The cookbook already supplies multi-turn rollout and training machinery. We will adapt its environment interface to use a table and parser rather than pay another model to answer. Its current group advantages are mean-centered, so the requested standard-deviation normalization needs an explicit adapter when we reach RL.
