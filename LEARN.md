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

## Main A11: useful questions, risky guesses and transfer

We resumed the same hosted model from update 0 after checking the saved seed, data order, counters and every known outstanding future. A future ID identifies work that may already have happened; a 408 means keep collecting it. The two unavailable turns each received one identical replacement, with the old output excluded and its money still held. The replacement layer enforces those limits before dispatch. No initialization or partial optimizer step was repeated.

Thirty updates improved noiseless animal EIG from 0.158 to 0.634 across the frozen sizes. The eight-case development curve improved early, then fluctuated. Guess-with-k explains why shorter winning games are not enough: 48/56 noiseless animal games still guessed with several candidates left. A lucky winning path can use fewer than log2(N) questions without exceeding the one-bit expected-information ceiling. Of 30 groups, 29 had reward variance but only 21 had win variance; two losing groups differed only through penalties. EIG remained a measurement, never a training reward.

Transfer got worse. Every one of the trained model's 276 synthetic invalid questions changed the prefix of a real attribute name; most combined its table code with the name's numeric suffix. For example, code b maps to a_600029, but b_600029 is neither valid form. The safe parser correctly rejects it. Valid synthetic questions still have high EIG, so end-to-end transfer failure does not prove that balanced splitting disappeared. We keep the original scores, report the copying error and uncertain guesses, and wait at the gate before changing anything. [MAIN_A11_GATE.md](MAIN_A11_GATE.md) records the full curve, intervals, costs and remaining-run estimate.

## Permanent endpoint storage, before A23

A downloaded adapter is useful only when the platform permits loading it again. This account cannot upload external weights, and A11's hosted files expired. We keep its local archive, but its deferred suffix and hard-mode evaluations cannot run. Named native saves solve that availability problem. The smoke test saves both training state and sampler weights without expiry, finishes the source session, and samples from a new client. The console must also show the files and their expiry before the test files are deleted and A23 starts. Storage has its own priced holds; removing a file does not settle an unknown bill. The science settings stay fixed, and the diagnostic parser stays outside primary training and scoring.

## API verification before the A23 confirmation

We can verify persistence without opening a browser. The API lists the saved test files with their exact names, paths, byte counts and expiration values. A new client then samples from the listed sampler path after the saving session has finished. The user checks the console separately and confirms before A23. We leave both test files in place for that check, and the existing storage holds stay reserved.

## A23: replication, stopping and durable endpoints

We repeated the unchanged 30-update A condition from fresh base weights with seed 23. Its animal questions improve relative to base, but less than A11. Synthetic search stays close to the already strong base policy instead of reproducing A11's copying failures. Repeating a training seed matters: one successful curve does not describe every outcome. The same eight development cases show an early improvement followed by fluctuations, and remain too small to settle the size of that gain.

Guess-with-k reveals two ways to fail. A11 often guesses too early at large N. A23 usually keeps asking until the budget ends and never guesses. Zero legal item-equality questions also hides malformed attempts: a separate raw-text audit finds bare candidate names and name lists, while the parser continues to reject and penalize them. Measuring those attempts changes no reward or score. EIG remains measurement only.

Both native A23 checkpoint types were saved without expiry and used by fresh clients after the training session ended. We collected every scheduled endpoint evaluation immediately. The API confirmed deletion of the two smoke files, but deletion does not settle storage billing, so their holds remain. The suffix parser is a labelled diagnostic only. Some matching prompts and seeds still produce different fresh-session actions before any parser mapping; we report that variation rather than assigning every score difference to the parser.

A growing JSON ledger also made its synchronous bookkeeping slow enough to delay the HTTP collector. A disposable-copy profile measured that work without changing the live ledger. After draining requests, we reduced execution concurrency from 16 games to 2; reservations, polling, prompts, rewards, seeds and model caps stayed unchanged. All paid work is now drained, the results reproduce from Git archives without credentials or raw caches, and we stop before B41. [MAIN_A23_GATE.md](MAIN_A23_GATE.md) records the measurements and remaining budget.

## Before B41: a transactional ledger and the budget the model sees

The old guard reread and rewrote the entire JSON ledger during every request. At 45,033 entries this delayed the same event loop that collected model responses. We migrated live state to SQLite: a transaction checks integer microdollar totals, changes one indexed reservation and appends its change record before the network callback can run. The existing cap, 1.5x hold, request IDs, 408 behavior and unknown-cost holds are unchanged. The full ledger.json remains an explicit audit export, written offline after collection, rather than on every turn. A missing database fails closed instead of falling back to stale spending totals.

Migration preserved every entry and approval, with identical usage and holds. All original budget tests also run on SQLite; mocked sampling, training and recovery contracts do too. A disposable-copy benchmark measured about 6.7 ms per guarded operation and 87 ms maximum event-loop delay with 16 simulated players, so execution returns to 16. These numbers describe local bookkeeping, not faster model inference.

The model sees the fixed maximum in its opening settings and the full action history. It does not see a running question count or a budget-exhausted notice. All 110 A23 extra ASK actions had the fixed maximum in context; none had an explicit remaining count. We recorded that distinction without changing any prompt. B41 will test noisy training under the same observations and reward.

## B41: more informative questions still need a stopping policy

The noisy seed completed the same 30 updates from fresh provider weights. Its small noiseless development check improved, but all four N=128 training groups had no wins. Across eight zero-win groups, the advantage differences came only from penalties: they reinforced cheaper losing behavior without a successful-search contrast. Each group shares one table, target and noise schedule, so eight rollouts are not eight independent worlds. On the frozen bank it asks better animal questions than base while guessing ambiguously in 203/280 games. It almost always finishes with a guess, unlike A23, which leaves 136 games without one. A11 and A23 have nearly the same noiseless animal wins but opposite failure modes; B41 makes the gambling pattern visible again.

Noisy wins are 36/140 for B41, versus 31 and 29 for the two A seeds. That difference has a wide interval and there is only one noisy training seed. Re-check counts also have different opportunity denominators. Higher EIG does not establish learned noise correction or a reliable search strategy. All three policies keep using attributes rather than legal item-name enumeration. B41 nevertheless has malformed candidate-name references in training and a smaller synthetic header-copying regression at evaluation. We keep those failures in the scores.

The ledger migration removed whole-history JSON work from request collection, and the run finished at 16-game concurrency without a lost request or replacement. Both native endpoint files have no expiry. We exported the final ledger after closing the service session and archived 84,310 append-only change records, which reconstruct all 54,866 current reservations exactly. Costs and old unknown holds remain intact. The final analysis reproduces from saved games and the JSON export without credentials or the live database. [MAIN_B41_GATE.md](MAIN_B41_GATE.md) records all seeds, intervals, checks and the stop.

## Visible-budget follow-up: expose a missing piece of state

The original prompt told the model the maximum number of questions but made it count how many it had used. We added a public counter on every turn and a direct GUESS instruction when it reached zero. We evaluated the same frozen games with raw base and the permanent A23/B41 endpoints. No weights, rewards, grammar, caps or scoring changed. New prompt hashes and scores live separately from the main study.

This small observation change removes every final extra ASK. A23's no-guess endings fall from 136 to zero and its wins rise from 138 to 186. B41 wins rise from 127 to 156, while raw stays at 141. The counter still leaves gambling: B41 makes 188 ambiguous guesses with questions left, and A23's count increases from 20 to 27. Raw also has 12 context-limit losses. A model following an explicit final instruction does not show that RL taught it when enough evidence has been gathered.

We keep both conditions because the difference teaches us something about the experiment: supplied state included candidate names, but omitted a running budget. Winning, choosing informative questions and deciding when to guess are distinct measurements. EIG falls under the counter even where wins improve. The follow-up cost $3.580565, every old hold remains, and all 226 tests plus exact replay checks pass. The project is stopped at this gate before further training or the final write-up.

## Write-up: connect claims to saved evidence

We built one derived data file with hashes of its sources, then used it for six chart designs in PNG and SVG. The report keeps the primary prompt and the visible-budget prompt separate. This matters because A23's noisy winning changes when budget state is shown, even though its weights do not change. Better questions, winning and deciding when to stop are separate outcomes.

The confidence intervals resample complete games within cells. They describe each saved endpoint. A separate analysis resamples the two A seeds before games, but there are too few seeds to estimate training variability well. The small development curves get a clear label so they do not stand in for noisy or large-candidate evaluation.

The videos replay saved actions and posterior arrays through the existing viewer. A11's missing hosted checkpoint does not prevent replaying its collected transcript. A numeric-order rule selects the behavior contrasts. It picks a case where base wins and both trained models lose. The noisy budget example ends in a correct guess while several candidates remain, so a win is not a certificate of certainty.

Every new figure, media export and thread post has a local source or validation record. The thread stays a draft for the user's review. All 226 tests pass, the ledger and primary artifacts stay unchanged, and the write-up adds zero Tinker usage. The experimental phase is closed.

## Publication: check what a clone exposes

The publication audit checks Git history as well as current files, including compressed game logs. Deleting a credential from a current file would not erase an older copy. The configured API key has no match in the public files or history. Local credentials, run state and adapter weights stay ignored. The user approved keeping the university email already present in commit metadata, so no history rewrite is needed.

The MIT license covers project code and authored data. Bundled assets keep their existing licenses. The README now names FFmpeg as a verification dependency and links to the public repository. Its offline commands read archived results and use mocked service tests. Publication does not authorize new Tinker work or posting the thread.

## Tokenizer tests: make cache requirements explicit

The clean-clone check exposed five tests that use real tokenizer files. Their service requests are mocked, but tokenization still depends on public assets that were only present in the original checkout's ignored cache. Those five tests now skip when their required files are missing. The message names the files and the command that downloads them. A corrupt or incompatible tokenizer still fails its test.

The download command uses the already pinned revisions for Qwen3-8B and the historical reference, requests only tokenizer assets and disables authentication. Archived-result analysis needs none of these assets. The README keeps dependency setup, offline analysis and complete tokenizer integration tests separate. Experimental prompts, scoring, frozen games, ledger entries and training code are unchanged.

The clean-clone verification passed all four analysis commands with zero downloads or network attempts. Its empty-cache suite passed 221 tests and skipped five. After the public tokenizer download, all 226 passed offline. The downloaded Qwen snapshot embeds its chat template in tokenizer_config.json, while the reference has a separate chat_template.jinja. File requirements follow those pinned layouts. Every regenerated artifact was byte-for-byte unchanged, and the release preserves the full original history. research/publication_checks.json records the checks and links to both test logs.
