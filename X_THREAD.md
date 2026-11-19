# X thread draft

For user review only. Nothing has been posted. Text blocks are the posts; media and source notes are outside them.

## Post 1

```text
1/8 I trained an 8B model to play 20 Questions. Reward: win, minus question cost and invalid-question penalties.

Question quality improved in every seed. Stopping stayed unreliable: one seed gambled, another stalled, and the noisy-trained seed gambled too.
```

Media: [headline.png](results/writeup/charts/headline.png)

Source: [RESULTS.md](RESULTS.md). Length: 257 characters under URL weighting.

## Post 2

```text
2/8 The game uses a binary attribute table and an exact Boolean grammar. The model sees the table and gets candidate state after each answer.

We measure expected information gain per question. It never enters the reward. No judge model scores the questions.
```

Media: [gamble-stall.mp4](replays/study/gamble-stall.mp4)

Source: [PROTOCOL.md](PROTOCOL.md). Length: 258 characters under URL weighting.

## Post 3

```text
3/8 On noiseless animals, expected bits/question rose from base 0.158 to 0.634, 0.390 and 0.437 across the three seeds. The ceiling is 1 bit.

All improved; none reached optimal search. Error bars resample games within each fitted endpoint, not training seeds.
```

Media: [animal-eig.png](results/writeup/charts/animal-eig.png)

Source: [results/writeup/numbers.json](results/writeup/numbers.json). Length: 260 characters under URL weighting.

## Post 4

```text
4/8 Win rate hides the policy. Two truthful-trained seeds won 24/56 and 25/56 noiseless animal games.

A11 lost the other 32 through ambiguous wrong guesses. A23 left 31 without guessing. Nearly the same wins, opposite failures. The replay uses a disclosed selection rule.
```

Media: [different-failures.png](results/writeup/charts/different-failures.png)

Source: [results/writeup/numbers.json](results/writeup/numbers.json). Length: 272 characters under URL weighting.

## Post 5

```text
5/8 Then we added one observation: Questions left: k of K. At zero: You must GUESS now. No more training.

A23's no-guess endings fell from 136 to 0. Wins rose from 138 to 186 out of 280. Its stalling depended on missing explicit budget state.
```

Media: [budget-fix.mp4](replays/study/budget-fix.mp4)

Source: [VISIBLE_BUDGET_GATE.md](VISIBLE_BUDGET_GATE.md). Length: 243 characters under URL weighting.

## Post 6

```text
6/8 Gambling persisted: B41 still made ambiguous guesses with budget left in 188/280 games, down from 202.

Under the primary prompt it won 36/140 noisy games, versus base 52/140. No clear noise-training benefit. The budget fix and question quality are separate findings.
```

Media: [visible-budget.png](results/writeup/charts/visible-budget.png)

Source: [results/visible_budget/summary.json](results/visible_budget/summary.json). Length: 271 characters under URL weighting.

## Post 7

```text
7/8 Limits: 2 truthful-training seeds, 1 noisy seed, 28 games per cell. Candidate state is supplied; thinking is disabled.

Synthetic transfer was mixed. A11's identifier errors did not repeat at the same scale in A23. Small development curves also missed large-N failures.
```

Media: [development.png](results/writeup/charts/development.png)

Source: [RESULTS.md](RESULTS.md). Length: 273 characters under URL weighting.

## Post 8

```text
8/8 $23.68 recorded Tinker usage, plus $2.08 held pending reconciliation.

Code, frozen games, CIs, failures and rule-selected replays are in the repo. No eval case entered training.

https://github.com/mohi-devhub/twenty-bits
```

Media: None. Repository link only.

Source: [ledger.json](ledger.json). Length: 207 characters under URL weighting.
