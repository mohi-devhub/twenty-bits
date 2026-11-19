# Visible-budget evaluation gate

This is a labelled evaluation-only prompt intervention on fixed policies. The main study is complete; these results do not replace any primary score. No training or checkpoint selection ran. All available policies completed the same 280 frozen games (indices 0–27 in each of ten cells). A11: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**.

Each user turn adds `Questions left: k of K`; k=0 also adds `No questions left. You must GUESS now.` Everything else is unchanged. The initial table/rules prefix stays byte-identical, and the original prompt hashes remain untouched. [Protocol](VISIBLE_BUDGET_PROTOCOL.md), [new hashes](evals/visible_budget/prompt_hashes.json), [full paired estimates](results/visible_budget/summary.json).

## What changed

**Raw:** showing budget reduces stalling (70 → 12/280 no-guess endings) and reduces ambiguous guessing with budget left (104 → 89/280). Wins 141 → 141/280; EIG 0.405 → 0.353 bits/question. Extra ASK at the final opportunity: 65 → 0.

**A23:** showing budget removes stalling (136 → 0/280 no-guess endings) and increases ambiguous guessing with budget left (20 → 27/280). Wins 138 → 186/280; EIG 0.466 → 0.457 bits/question. Extra ASK at the final opportunity: 136 → 0.

**B41:** showing budget removes stalling (1 → 0/280 no-guess endings) and reduces ambiguous guessing with budget left (202 → 188/280). Wins 127 → 156/280; EIG 0.540 → 0.491 bits/question. Extra ASK at the final opportunity: 1 → 0.

A lower no-guess rate can reflect more wrong guesses rather than better search. No-guess counts include context-limit losses, so they are broader than repeated-ASK stalling; the table below separates context exhaustion and extra final ASK. Ambiguous guessing is a behavior count, not automatically an error: noisy display size is a fixed thresholded posterior list. This follow-up does not establish a learned stopping strategy.

The counter removes final-opportunity ASK stalling in every available policy. All 12 remaining raw no-guess endings are context-limit losses. Gambling is reduced overall for raw and B41, while A23's overall count increases. At noisy animals N=128, B41 still guesses ambiguously with budget left in 28/28 games. The prompt intervention begins on the initial turn, so question choices and stopping can both change.

Noisy wins change raw 52→57, A23 29→74 and B41 36→55, each out of 140. A23's noisy EIG is nearly unchanged (0.3548→0.3540 bits/question). The primary finding that trained endpoints have fewer noisy wins than raw base therefore depends on the original observation format; it does not carry over to A23 under visible budget. These are separately labelled fixed-policy outcomes.

## Paired cells

Every arrow is **primary without a dynamic counter → visible budget**, on the same 28 games. EIG is ratio of summed question EIG to questions, including invalids and losses. Ambiguous-with-budget-left and no-guess percentages use all 28 games. Extra ASK is a game count at the final-guess opportunity, not an extra question in the question denominator. Early wins are correct guesses before ceil(log2 N); the complete data also include their conditional success fraction.

### Raw

| Domain | N | Noise | Wins /28 | EIG bits/Q | Ambiguous with budget left | No guess | Extra ASK at end | Early wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| animals | 32 | 0.00 | 5 → 5 | 0.207 → 0.195 | 4 (14.3%) → 13 (46.4%) | 15 (53.6%) → 0 (0.0%) | 15 → 0 | 0 → 1 |
| animals | 32 | 0.10 | 4 → 3 | 0.121 → 0.094 | 10 (35.7%) → 12 (42.9%) | 15 (53.6%) → 0 (0.0%) | 15 → 0 | 0 → 0 |
| animals | 128 | 0.00 | 2 → 0 | 0.109 → 0.059 | 7 (25.0%) → 4 (14.3%) | 19 (67.9%) → 5 (17.9%) | 16 → 0 | 0 → 0 |
| animals | 128 | 0.10 | 2 → 0 | 0.087 → 0.039 | 20 (71.4%) → 5 (17.9%) | 8 (28.6%) → 7 (25.0%) | 6 → 0 | 0 → 0 |
| synthetic | 32 | 0.00 | 26 → 24 | 0.717 → 0.639 | 0 (0.0%) → 0 (0.0%) | 2 (7.1%) → 0 (0.0%) | 2 → 0 | 3 → 4 |
| synthetic | 32 | 0.10 | 9 → 14 | 0.405 → 0.354 | 8 (28.6%) → 7 (25.0%) | 11 (39.3%) → 0 (0.0%) | 11 → 0 | 0 → 0 |
| synthetic | 128 | 0.00 | 28 → 27 | 0.893 → 0.782 | 0 (0.0%) → 1 (3.6%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 4 → 3 |
| synthetic | 128 | 0.10 | 17 → 19 | 0.458 → 0.402 | 26 (92.9%) → 22 (78.6%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |
| synthetic | 256 | 0.00 | 28 → 28 | 0.858 → 0.860 | 1 (3.6%) → 0 (0.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 5 → 5 |
| synthetic | 256 | 0.10 | 20 → 21 | 0.476 → 0.428 | 28 (100.0%) → 25 (89.3%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |

### A23

| Domain | N | Noise | Wins /28 | EIG bits/Q | Ambiguous with budget left | No guess | Extra ASK at end | Early wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| animals | 32 | 0.00 | 20 → 21 | 0.489 → 0.528 | 0 (0.0%) → 1 (3.6%) | 8 (28.6%) → 0 (0.0%) | 8 → 0 | 3 → 2 |
| animals | 32 | 0.10 | 2 → 13 | 0.320 → 0.295 | 1 (3.6%) → 0 (0.0%) | 25 (89.3%) → 0 (0.0%) | 25 → 0 | 0 → 0 |
| animals | 128 | 0.00 | 5 → 9 | 0.291 → 0.279 | 0 (0.0%) → 7 (25.0%) | 23 (82.1%) → 0 (0.0%) | 23 → 0 | 0 → 1 |
| animals | 128 | 0.10 | 2 → 3 | 0.189 → 0.222 | 0 (0.0%) → 5 (17.9%) | 25 (89.3%) → 0 (0.0%) | 25 → 0 | 0 → 0 |
| synthetic | 32 | 0.00 | 28 → 28 | 0.846 → 0.837 | 0 (0.0%) → 0 (0.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 5 → 6 |
| synthetic | 32 | 0.10 | 0 → 16 | 0.410 → 0.403 | 0 (0.0%) → 0 (0.0%) | 28 (100.0%) → 0 (0.0%) | 28 → 0 | 0 → 0 |
| synthetic | 128 | 0.00 | 28 → 28 | 0.877 → 0.860 | 0 (0.0%) → 0 (0.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 3 → 3 |
| synthetic | 128 | 0.10 | 9 → 22 | 0.431 → 0.425 | 5 (17.9%) → 2 (7.1%) | 18 (64.3%) → 0 (0.0%) | 18 → 0 | 0 → 0 |
| synthetic | 256 | 0.00 | 28 → 26 | 0.857 → 0.744 | 0 (0.0%) → 0 (0.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 4 → 4 |
| synthetic | 256 | 0.10 | 16 → 20 | 0.426 → 0.414 | 14 (50.0%) → 12 (42.9%) | 9 (32.1%) → 0 (0.0%) | 9 → 0 | 0 → 0 |

### B41

| Domain | N | Noise | Wins /28 | EIG bits/Q | Ambiguous with budget left | No guess | Extra ASK at end | Early wins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| animals | 32 | 0.00 | 15 → 19 | 0.542 → 0.464 | 20 (71.4%) → 15 (53.6%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 4 → 1 |
| animals | 32 | 0.10 | 6 → 12 | 0.317 → 0.317 | 28 (100.0%) → 26 (92.9%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |
| animals | 128 | 0.00 | 4 → 7 | 0.332 → 0.304 | 25 (89.3%) → 21 (75.0%) | 1 (3.6%) → 0 (0.0%) | 1 → 0 | 0 → 0 |
| animals | 128 | 0.10 | 0 → 2 | 0.250 → 0.221 | 28 (100.0%) → 28 (100.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |
| synthetic | 32 | 0.00 | 25 → 26 | 0.837 → 0.853 | 4 (14.3%) → 2 (7.1%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 5 → 6 |
| synthetic | 32 | 0.10 | 14 → 17 | 0.443 → 0.422 | 28 (100.0%) → 26 (92.9%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |
| synthetic | 128 | 0.00 | 26 → 28 | 0.832 → 0.875 | 5 (17.9%) → 3 (10.7%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 3 → 4 |
| synthetic | 128 | 0.10 | 10 → 13 | 0.496 → 0.466 | 28 (100.0%) → 28 (100.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |
| synthetic | 256 | 0.00 | 21 → 21 | 0.871 → 0.804 | 9 (32.1%) → 11 (39.3%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 6 → 4 |
| synthetic | 256 | 0.10 | 6 → 11 | 0.479 → 0.475 | 27 (96.4%) → 28 (100.0%) | 0 (0.0%) → 0 (0.0%) | 0 → 0 | 0 → 0 |

## Paired uncertainty

95% percentile intervals resample 10,000 paired complete games within each cell, sharing case draws between noise variants. Policies are fixed; no training-seed uncertainty is estimated. All comparisons are exploratory and have no multiplicity adjustment. The small cells limit precision.

| Policy | Domain | N | Noise | Win-rate change [95% CI], percentage points | EIG change [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| Raw | animals | 32 | 0.00 | +0.0 [-17.9, +17.9] | -0.012 [-0.104, +0.073] |
| Raw | animals | 32 | 0.10 | -3.6 [-17.9, +7.1] | -0.027 [-0.074, +0.018] |
| Raw | animals | 128 | 0.00 | -7.1 [-17.9, +0.0] | -0.050 [-0.104, +0.002] |
| Raw | animals | 128 | 0.10 | -7.1 [-17.9, +0.0] | -0.048 [-0.086, -0.012] |
| Raw | synthetic | 32 | 0.00 | -7.1 [-21.4, +7.1] | -0.078 [-0.246, +0.092] |
| Raw | synthetic | 32 | 0.10 | +17.9 [-3.6, +39.3] | -0.051 [-0.106, -0.006] |
| Raw | synthetic | 128 | 0.00 | -3.6 [-10.7, +0.0] | -0.111 [-0.238, -0.003] |
| Raw | synthetic | 128 | 0.10 | +7.1 [-10.7, +25.0] | -0.056 [-0.107, -0.018] |
| Raw | synthetic | 256 | 0.00 | +0.0 [+0.0, +0.0] | +0.002 [-0.015, +0.021] |
| Raw | synthetic | 256 | 0.10 | +3.6 [-10.7, +17.9] | -0.048 [-0.059, -0.037] |
| A23 | animals | 32 | 0.00 | +3.6 [-10.7, +17.9] | +0.038 [-0.072, +0.155] |
| A23 | animals | 32 | 0.10 | +39.3 [+21.4, +57.1] | -0.025 [-0.056, +0.003] |
| A23 | animals | 128 | 0.00 | +14.3 [-7.1, +35.7] | -0.012 [-0.073, +0.049] |
| A23 | animals | 128 | 0.10 | +3.6 [-7.1, +14.3] | +0.034 [+0.002, +0.065] |
| A23 | synthetic | 32 | 0.00 | +0.0 [+0.0, +0.0] | -0.009 [-0.048, +0.031] |
| A23 | synthetic | 32 | 0.10 | +57.1 [+39.3, +75.0] | -0.007 [-0.018, +0.001] |
| A23 | synthetic | 128 | 0.00 | +0.0 [+0.0, +0.0] | -0.017 [-0.078, +0.039] |
| A23 | synthetic | 128 | 0.10 | +46.4 [+25.0, +67.9] | -0.006 [-0.013, -0.000] |
| A23 | synthetic | 256 | 0.00 | -7.1 [-17.9, +0.0] | -0.112 [-0.246, -0.005] |
| A23 | synthetic | 256 | 0.10 | +14.3 [-3.6, +32.1] | -0.011 [-0.027, +0.002] |
| B41 | animals | 32 | 0.00 | +14.3 [-3.6, +32.1] | -0.077 [-0.171, +0.014] |
| B41 | animals | 32 | 0.10 | +21.4 [+7.1, +35.7] | -0.000 [-0.026, +0.026] |
| B41 | animals | 128 | 0.00 | +10.7 [-3.6, +25.0] | -0.028 [-0.079, +0.022] |
| B41 | animals | 128 | 0.10 | +7.1 [+0.0, +17.9] | -0.029 [-0.070, +0.017] |
| B41 | synthetic | 32 | 0.00 | +3.6 [-7.1, +14.3] | +0.016 [-0.020, +0.057] |
| B41 | synthetic | 32 | 0.10 | +10.7 [+0.0, +25.0] | -0.020 [-0.033, -0.009] |
| B41 | synthetic | 128 | 0.00 | +7.1 [+0.0, +17.9] | +0.043 [-0.041, +0.154] |
| B41 | synthetic | 128 | 0.10 | +10.7 [-3.6, +25.0] | -0.030 [-0.041, -0.021] |
| B41 | synthetic | 256 | 0.00 | +0.0 [-21.4, +17.9] | -0.067 [-0.169, +0.001] |
| B41 | synthetic | 256 | 0.10 | +17.9 [+0.0, +35.7] | -0.004 [-0.045, +0.061] |

## Other failure measurements

All arrows retain the same primary → visible-budget order. Truncation counts turns; context exhaustion counts games and applies the unchanged prompt-plus-output-cap rule. The full per-cell JSON retains these counts.

| Policy | Invalid questions | Truncated turns | Context-limit losses | Format-error turns |
| --- | ---: | ---: | ---: | ---: |
| Raw | 349 → 519 | 103 → 203 | 5 → 12 | 65 → 0 |
| A23 | 76 → 101 | 0 → 0 | 0 → 0 | 136 → 0 |
| B41 | 30 → 22 | 0 → 0 | 0 → 0 | 1 → 0 |

## Spend and verification

The frozen forecast was **$7.845394 including 1.5 margin**, versus **$3.580565 recorded usage + $0 unresolved follow-up holds** under the $8 ceiling. It credited 70% cached input versus an observed prior minimum of 88.6%, added 15% behavior allowance, then applied the margin. The uncached replay was $10.105634; caching was an explicit forecast assumption, not a guarantee.

Project usage is **$23.681223**, all holds **$2.083181**, leaving **$24.235596 of $50**. These are observed-token charges at pinned rates; invoice reconciliation is pending. All older lost-original and storage holds remain. No new checkpoint save or storage reservation was needed.

| Policy | Input tokens | Cache-hit tokens | Cache fraction | Output tokens | Visible reasoning tokens | Usage USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw | 23,754,949 | 21,291,008 | 89.6% | 492,415 | 0 | 1.607880 |
| A23 | 20,463,890 | 18,745,472 | 91.6% | 27,952 | 0 | 1.084586 |
| B41 | 16,076,787 | 14,504,960 | 90.2% | 24,151 | 0 | 0.888099 |

All 9,448 native prompt sequences match the cookbook renderer and saved request signatures. All 9,448 accepted requests saved deterministic IDs before HTTP dispatch and verified receipts. Actions, answers, seeded flips, posteriors, EIG and rewards replay exactly under the unchanged game. No gradient, optimizer or checkpoint-save operations ran. Every primary artifact captured in the preflight still has its original hash.

No request was lost and no replacement ran in this follow-up.

The service session is finished and HTTP work is drained. The gate includes 226 passing unit tests, archived accepted responses and exclusions, a separate ledger event export and credential-free replay verification. Thinking remains disabled; zero visible reasoning tokens do not measure internal computation.

## Stop

Stopped at this gate. The user will decide between a training follow-up and the final write-up phase. No more main seeds, training, final replay/video, results article or X thread has started.
