# Saved example games

The selection rules are fixed in results/writeup/numbers.json. These are behavior-filtered illustrations. Aggregate figures use every declared game. Viewer counters, target outlines and hidden flip annotations are for the reader. They are not added to primary model prompts.

## Same target, different failures

`paid-v1/animals/32/1/p0`

Target: `juvenile_female_arctic_fox`.

Animals, p=0. Sort N ascending, then frozen index numerically ascending. Take the earliest case where A11 makes an ambiguous wrong guess with questions left and A23 never guesses. The raw control uses that same case, without an outcome filter.

23 cases meet the rule.

### Raw

| Action | Questions left before action | Displayed candidates before action | Exact action | Answer | EIG |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 10 | 32 | `ASK: am` | YES | 0.757878 |
| 2 | 9 | 25 | `ASK: am AND NOT w` | NO | 0.634310 |
| 3 | 8 | 21 | `ASK: am AND t` | YES | 0.998364 |
| 4 | 7 | 11 | `ASK: am AND t AND NOT y` | YES | 0.994030 |
| 5 | 6 | 5 | `ASK: am AND t AND NOT y AND NOT ax` | YES | 0.970951 |
| 6 | 5 | 3 | `ASK: am AND t AND NOT y AND NOT ax AND NOT ap` | YES | 0.918296 |
| 7 | 4 | 2 | `ASK: am AND t AND NOT y AND NOT ax AND NOT ap AND NOT an` | YES | 1.000000 |
| 8 | 3 | 1 | `GUESS: juvenile_female_arctic_fox` | WIN | 0.000000 |

Outcome: win. Questions used: 7.

### A11

| Action | Questions left before action | Displayed candidates before action | Exact action | Answer | EIG |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 10 | 32 | `ASK: w` | YES | 0.928362 |
| 2 | 9 | 21 | `ASK: t` | YES | 0.998364 |
| 3 | 8 | 11 | `ASK: y` | NO | 0.994030 |
| 4 | 7 | 5 | `ASK: r` | NO | 0.970951 |
| 5 | 6 | 3 | `ASK: m` | YES | 0.918296 |
| 6 | 5 | 2 | `GUESS: adult_female_aardvark` | LOSS | 0.000000 |

Outcome: loss. Questions used: 5.

### A23

| Action | Questions left before action | Displayed candidates before action | Exact action | Answer | EIG |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 10 | 32 | `ASK: am` | YES | 0.757878 |
| 2 | 9 | 25 | `ASK: w` | YES | 0.634310 |
| 3 | 8 | 21 | `ASK: t` | YES | 0.998364 |
| 4 | 7 | 11 | `ASK: am` | YES | 0.000000 |
| 5 | 6 | 11 | `ASK: r` | NO | 0.945660 |
| 6 | 5 | 7 | `ASK: ae` | NO | 0.985228 |
| 7 | 4 | 4 | `ASK: ab` | NO | 0.000000 |
| 8 | 3 | 4 | `ASK: ac` | NO | 0.000000 |
| 9 | 2 | 4 | `ASK: ag` | NO | 0.000000 |
| 10 | 1 | 4 | `ASK: an` | NO | 0.811278 |
| 11 | 0 | 3 | `ASK: ai` | LOSS | 0.000000 |

Outcome: loss. Questions used: 10.

## Same weights, visible budget

`paid-v1/animals/32/1/p0.1`

Target: `juvenile_female_arctic_fox`.

Animals, p=0.10. Sort N ascending, then frozen index numerically ascending. Take the earliest case where A23 primary never guesses and its visible-budget rollout wins. Do not filter question text, target, EIG or game length.

13 cases meet the rule.

### A23 primary

| Action | Questions left before action | Displayed candidates before action | Exact action | Answer | EIG |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 10 | 32 | `ASK: am` | YES | 0.379553 |
| 2 | 9 | 32 | `ASK: w` | NO | 0.339538 |
| 3 | 8 | 32 | `ASK: am` | YES | 0.227217 |
| 4 | 7 | 32 | `ASK: ar` | YES | 0.496299 |
| 5 | 6 | 25 | `ASK: az` | NO | 0.441775 |
| 6 | 5 | 32 | `ASK: n` | YES | 0.530919 |
| 7 | 4 | 28 | `ASK: f` | NO | 0.510137 |
| 8 | 3 | 26 | `ASK: m` | YES | 0.527843 |
| 9 | 2 | 26 | `ASK: bc` | YES | 0.419949 |
| 10 | 1 | 13 | `ASK: t` | YES | 0.097519 |
| 11 | 0 | 9 | `ASK: y` | LOSS | 0.000000 |

Outcome: loss. Questions used: 10.

### A23 visible budget

| Action | Questions left before action | Displayed candidates before action | Exact action | Answer | EIG |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 10 | 32 | `ASK: am` | YES | 0.379553 |
| 2 | 9 | 32 | `ASK: w` | NO | 0.339538 |
| 3 | 8 | 32 | `ASK: t` | YES | 0.342283 |
| 4 | 7 | 32 | `ASK: y` | NO | 0.498955 |
| 5 | 6 | 32 | `ASK: am` | YES | 0.275478 |
| 6 | 5 | 32 | `ASK: t` | YES | 0.526027 |
| 7 | 4 | 21 | `ASK: r` | NO | 0.490606 |
| 8 | 3 | 21 | `ASK: n` | YES | 0.513415 |
| 9 | 2 | 16 | `ASK: ae` | NO | 0.501517 |
| 10 | 1 | 13 | `ASK: am` | YES | 0.139370 |
| 11 | 0 | 13 | `GUESS: juvenile_female_arctic_fox` | WIN | 0.000000 |

Outcome: win. Questions used: 10.

The noisy visible-budget example wins with 13 displayed candidates and target posterior about 0.571. A correct guess here does not imply certainty. The display threshold is 0.001 plus MAP, while scoring retains the full posterior. See games.json for all saved posterior arrays.
