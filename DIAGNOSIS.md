# Phase 2 failure diagnosis

The saved games contain a grammar and termination failure before there is a useful search-policy comparison. Qwen made three guesses, all wrong, in 280 games. It produced 447 valid questions, all with item equalities. The reference never guessed in 20 games. This diagnosis makes zero service calls and reads only accepted, saved Phase 2 outputs. The five older orphaned outputs remain excluded.

## Every generated turn

Valid ASK, valid GUESS, INVALID and other partition generated turns. A valid GUESS names a listed candidate with one line, whether or not it is correct. Other includes a further ASK in the final-guess slot. Truncated and empty overlap the partition. An action can be both truncated and INVALID. Empty means no decoded action, not no generated reasoning. A second mutually exclusive partition with truncation priority is in [phase2.json](results/diagnosis/phase2.json).

| Model | Domain | N | p | Turns | Valid ASK | Valid GUESS | INVALID | Other | Truncated | Empty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-8B | animals | 32 | 0 | 308 | 96 | 0 | 184 | 28 | 171 | 0 |
| Qwen3-8B | animals | 32 | 0.1 | 306 | 137 | 1 | 141 | 27 | 114 | 0 |
| Qwen3-8B | animals | 128 | 0 | 401 | 62 | 1 | 324 | 14 | 227 | 0 |
| Qwen3-8B | animals | 128 | 0.1 | 403 | 52 | 1 | 337 | 13 | 203 | 0 |
| Qwen3-8B | synthetic | 32 | 0 | 308 | 10 | 0 | 270 | 28 | 11 | 0 |
| Qwen3-8B | synthetic | 32 | 0.1 | 308 | 20 | 0 | 260 | 28 | 0 | 0 |
| Qwen3-8B | synthetic | 128 | 0 | 396 | 56 | 0 | 336 | 4 | 296 | 0 |
| Qwen3-8B | synthetic | 128 | 0.1 | 393 | 14 | 0 | 378 | 1 | 354 | 0 |
| Qwen3-8B | synthetic | 256 | 0 | 368 | 0 | 0 | 367 | 1 | 351 | 0 |
| Qwen3-8B | synthetic | 256 | 0.1 | 368 | 0 | 0 | 367 | 1 | 351 | 0 |
| gpt-oss-120b | animals | 32 | 0 | 55 | 4 | 0 | 46 | 5 | 42 | 42 |
| gpt-oss-120b | animals | 32 | 0.1 | 55 | 1 | 0 | 49 | 5 | 34 | 34 |
| gpt-oss-120b | synthetic | 32 | 0 | 55 | 8 | 0 | 42 | 5 | 37 | 37 |
| gpt-oss-120b | synthetic | 32 | 0.1 | 55 | 6 | 0 | 44 | 5 | 44 | 44 |

## Parser and validation errors

Each INVALID receives one category based on its actual error. The parser reports the error it encounters; a longer expression can contain additional defects. Code means a table column code used where a full attribute name is required. Unknown name means a name outside the current table. Bad text or quote includes a generated token outside the grammar and cut-off quoted names. Truncation flags above prevent interpreting all such errors as independent grammar failures.

| Model | Domain | N | p | Code | Unknown attr | Unknown name | Missing ) | Missing == | Missing expr | Bad text/quote | Action format | Trailing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-8B | animals | 32 | 0 | 10 | 0 | 20 | 7 | 13 | 26 | 108 | 0 | 0 |
| Qwen3-8B | animals | 32 | 0.1 | 10 | 0 | 52 | 0 | 8 | 9 | 62 | 0 | 0 |
| Qwen3-8B | animals | 128 | 0 | 3 | 0 | 61 | 71 | 40 | 16 | 122 | 11 | 0 |
| Qwen3-8B | animals | 128 | 0.1 | 0 | 0 | 96 | 81 | 41 | 33 | 86 | 0 | 0 |
| Qwen3-8B | synthetic | 32 | 0 | 210 | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 0 |
| Qwen3-8B | synthetic | 32 | 0.1 | 220 | 0 | 0 | 31 | 0 | 0 | 0 | 0 | 9 |
| Qwen3-8B | synthetic | 128 | 0 | 54 | 0 | 0 | 126 | 14 | 0 | 142 | 0 | 0 |
| Qwen3-8B | synthetic | 128 | 0.1 | 24 | 0 | 0 | 126 | 26 | 16 | 186 | 0 | 0 |
| Qwen3-8B | synthetic | 256 | 0 | 16 | 0 | 0 | 234 | 39 | 13 | 65 | 0 | 0 |
| Qwen3-8B | synthetic | 256 | 0.1 | 16 | 0 | 0 | 221 | 65 | 13 | 52 | 0 | 0 |
| gpt-oss-120b | animals | 32 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 40 | 0 |
| gpt-oss-120b | animals | 32 | 0.1 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 34 | 0 |
| gpt-oss-120b | synthetic | 32 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 33 | 0 |
| gpt-oss-120b | synthetic | 32 | 0.1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 39 | 0 |

## How games end

Budget/no guess, wrong guess and context limit are exclusive terminal causes. Context limit takes precedence when the next rendered prompt plus the unchanged output allowance cannot fit. Invalid-heavy means at least half the counted questions were INVALID. Invalid-heavy and never-guessed are overlapping behavioral flags, not extra terminal causes. Across both models, 165 games ended at the budget without a guess, three ended with a wrong guess, and 132 hit the context limit. 297 of 300 never guessed.

| Model | Domain | N | p | Games | Budget/no guess | Wrong guess | Context limit | Invalid-heavy | Never guessed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-8B | animals | 32 | 0 | 28 | 28 | 0 | 0 | 19 | 28 |
| Qwen3-8B | animals | 32 | 0.1 | 28 | 27 | 1 | 0 | 14 | 27 |
| Qwen3-8B | animals | 128 | 0 | 28 | 14 | 1 | 13 | 24 | 27 |
| Qwen3-8B | animals | 128 | 0.1 | 28 | 13 | 1 | 14 | 25 | 27 |
| Qwen3-8B | synthetic | 32 | 0 | 28 | 28 | 0 | 0 | 27 | 28 |
| Qwen3-8B | synthetic | 32 | 0.1 | 28 | 28 | 0 | 0 | 26 | 28 |
| Qwen3-8B | synthetic | 128 | 0 | 28 | 4 | 0 | 24 | 24 | 28 |
| Qwen3-8B | synthetic | 128 | 0.1 | 28 | 1 | 0 | 27 | 27 | 28 |
| Qwen3-8B | synthetic | 256 | 0 | 28 | 1 | 0 | 27 | 28 | 28 |
| Qwen3-8B | synthetic | 256 | 0.1 | 28 | 1 | 0 | 27 | 28 | 28 |
| gpt-oss-120b | animals | 32 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| gpt-oss-120b | animals | 32 | 0.1 | 5 | 5 | 0 | 0 | 5 | 5 |
| gpt-oss-120b | synthetic | 32 | 0 | 5 | 5 | 0 | 0 | 5 | 5 |
| gpt-oss-120b | synthetic | 32 | 0.1 | 5 | 5 | 0 | 0 | 5 | 5 |

## The 311 questions below 1e-12 EIG

Eight questions name only already-eliminated items. Zero name an item outside the candidate table. The other 303 consist of 82 predicates with an already-implied answer after elimination, 220 predicates constant on the entire table, and one with a nearly certain noisy posterior. Unknown names produce INVALID instead and are counted in the error table. The eight eliminated-item questions and 82 implied-answer questions together account for 90 predicates that became constant after noiseless elimination. All 220 full-table constants were true everywhere. The detailed audit found no false-for-all cases among the 303 other questions and found that all 303 were positive item-name OR lists. Repetition overlaps these causes: 281 repeated an earlier split or its complement. See [the detailed classification](results/diagnosis/zero_eig_other.json). The one near-certain case is a numerical threshold case, not an exact logical constant. [All 311 classifications](results/diagnosis/phase2.json) include both the requested name-based grouping and the semantic cause, table split, posterior mass, and count of named eliminated items.

## Why the reference also loses

Of its 220 turns, 157 hit the 512-token cap while still in the analysis channel. All 157 decode to an empty action. It generated 99,454 visible reasoning tokens out of 100,820 total generated tokens. Only 19 questions were valid; 35 more used column codes as unknown attributes. The 157 empty turns include final-slot failures, so the parser's action-format count is smaller. It made no GUESS. This is an analysis-budget and format failure. It does not establish that a sufficiently budgeted reference cannot solve the game. No reference rerun is authorized or charged here.

## Cost reconciles to token usage

Actual recorded usage is 1.958 times the $2.95805922 forecast. The forecast allowed full question budgets but only 64 Qwen output tokens per turn, 128 reference tokens, and 32 history-overhead tokens. It credited no cache hits. Actual Qwen outputs averaged about 1,488 tokens per turn. Their repeated inclusion in later contexts raised uncached input work as well as output work.

The bridge changes turn count at forecast lengths, then substitutes observed input lengths, observed output lengths, cache hits, and per-call upward rounding. The order is fixed and all rows add exactly before display rounding. Input changes include different initial prefixes and the much larger generated histories.

| USD component | Qwen3-8B | gpt-oss-120b | Total |
| --- | --- | --- | --- |
| forecast_usd | +2.801075 | +0.156984 | +2.958059 |
| turn_count_change_usd | -0.357671 | +0.000000 | -0.357671 |
| input_length_change_usd | +5.947631 | -0.057725 | +5.889906 |
| output_length_change_usd | +3.040010 | +0.061034 | +3.101045 |
| cache_credit_usd | -5.746092 | -0.053898 | -5.799990 |
| rounding_usd | +0.001764 | +0.000112 | +0.001875 |
| Recorded usage | 5.686718 | 0.106507 | 5.793225 |

| Model | Turns forecast / used | Input forecast / used | Output forecast / used | Cache-hit tokens | INVALID turns / cost |
| --- | --- | --- | --- | --- | --- |
| Qwen3-8B | 3,864 / 3,559 | 13,603,576 / 42,330,102 | 247,296 / 5,294,460 | 36,833,920 | 2,964 / $5.102452 |
| gpt-oss-120b | 220 / 220 | 404,030 / 229,105 | 28,160 / 100,820 | 204,160 | 181 / $0.089383 |

INVALID turns cost $5.191835, or 89.6% of the total. That is a subset of actual spend, not another additive explanation. Their later history also costs input tokens, already included in the input-length and cache rows. The $0.007195 in old orphan holds is separate. These are gross usage charges from saved token counts and rates, not finalized invoices. [Rate card](https://tinker-docs.thinkingmachines.ai/tinker/models.json).

## Three complete transcripts

These are deterministic category examples from saved games, not a performance sample. They include the full public table, settings, every raw generated response, decoded actions, and all answers. Targets are revealed only in the diagnostic files. No response text is shortened.

- [Qwen malformed and truncated questions](results/diagnosis/transcripts/qwen-malformed.md): animals N=32, index 0, p=0.
- [Qwen legal zero-information repetition](results/diagnosis/transcripts/qwen-zero-information.md): animals N=32, index 1, p=0.
- [Reference analysis truncation](results/diagnosis/transcripts/reference-analysis-only.md): animals N=32, index 0, p=0.

Reproduce with `.venv/bin/python scripts/diagnose_phase2.py`. The [source hash, exact bridge, partitions and categories](results/diagnosis/phase2.json) and [turn CSV](results/diagnosis/turns.csv) are saved.
