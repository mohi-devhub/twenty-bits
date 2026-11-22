# X thread draft

For user review only. Nothing has been posted. Text blocks are the posts; media and source notes are outside them.

## Post 1

```text
1/8 RL improved Qwen3-8B’s expected information per question on noiseless animals, about 4× for A11. Across 280 games per seed, A11 made 167 ambiguous wrong guesses, A23 ended 136 without guessing, and B41 made 202 ambiguous guesses with budget left.
```

Media: [guess-timing.png](figures/guess-timing.png)

Source: [RESULTS.md](RESULTS.md). Length: 250 characters under URL weighting.

## Post 2

```text
2/8 The game uses a binary attribute table and an exact Boolean grammar. The model sees the table and gets candidate state after each answer.

We measure expected information gain per question. It never enters the reward. No judge model scores the questions.
```

Media: [gamble-stall.mp4](replays/study/gamble-stall.mp4)

Source: [PROTOCOL.md](PROTOCOL.md). Length: 258 characters under URL weighting.

## Post 3

```text
3/8 On 28 matched noiseless N=32 games, the greedy reference won every game in 5 questions each. Raw Qwen3-8B won 5, random won 11, and the trained policies won 17, 20 and 15. Across the full 280-game bank, raw won 141, A11 104, A23 138 and B41 127.
```

Media: [submission-baselines.png](figures/submission-baselines.png)

Source: [results/submission/comparison.json](results/submission/comparison.json). Length: 249 characters under URL weighting.

## Post 4

```text
4/8 Win rate hides the policy. Two truthful-trained seeds won 24/56 and 25/56 noiseless animal games.

A11 lost the other 32 through ambiguous wrong guesses. A23 left 31 without guessing. Nearly the same wins, opposite failures. The replay uses a disclosed selection rule.
```

Media: [different-failures.png](results/writeup/charts/different-failures.png)

Source: [results/writeup/numbers.json](results/writeup/numbers.json). Length: 272 characters under URL weighting.

## Post 5

```text
5/8 We tested a prompt with a running question counter and a final-guess instruction. Same weights.

A23’s no-guess endings fell from 136 to 0 and wins rose from 138 to 186 out of 280. The intervention does not isolate either prompt change.
```

Media: [budget-fix.mp4](replays/study/budget-fix.mp4)

Source: [VISIBLE_BUDGET_GATE.md](VISIBLE_BUDGET_GATE.md). Length: 240 characters under URL weighting.

## Post 6

```text
6/8 B41 still guessed ambiguously with budget left in 188/280 games, down from 202. Under the primary prompt it won 36/140 noisy games, versus raw 52/140. Its noisy win-rate interval versus mean truthful-trained A includes zero. There was one noisy-training seed.
```

Media: [visible-budget.png](results/writeup/charts/visible-budget.png)

Source: [results/visible_budget/summary.json](results/visible_budget/summary.json). Length: 263 characters under URL weighting.

## Post 7

```text
7/8 Limits: candidate state is supplied, thinking is disabled, and we used one learning rate. The tested halving prompt made 262/280 invalid questions and no final guesses. A working prompted-halving baseline remains untested.
```

Media: [development.png](results/writeup/charts/development.png)

Source: [RESULTS.md](RESULTS.md). Length: 226 characters under URL weighting.

## Post 8

```text
8/8 Historical Tinker usage was $23.681223, plus $2.083181 held. Code, intervals, and full games are public. The held-out profiles share some underlying animal types with training. Frozen games never entered the main gradients.

https://github.com/mohi-devhub/twenty-bits
```

Media: None. Repository link only.

Source: [ledger.json](ledger.json). Length: 252 characters under URL weighting.
