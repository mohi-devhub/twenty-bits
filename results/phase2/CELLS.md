# Phase 2 cell measurements

Status: complete. Completed 300 of 300 approved games. Bootstrap intervals resample whole games 10,000 times.

Invalid is per question. Format errors and truncation are per generated turn. Enumeration is grammar-valid item equality; raw equality attempts include invalid or truncated outputs. Questions/win is undefined when there are no wins. Cache hits count reported prompt tokens.

| Model | Domain | N | p | Games | Win % | EIG/Q | Q/win | Enum % | Raw equality % | Invalid % | Format % | Truncation % | Cache hit tokens | Cost USD |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-8B | animals | 32 | 0 | 28 | 0.000 | 0.018 | — | 34.286 | 100.000 | 65.714 | 9.091 | 55.519 | 1,959,680 | 0.397946 |
| Qwen/Qwen3-8B | animals | 32 | 0.1 | 28 | 0.000 | 0.025 | — | 49.281 | 100.000 | 50.719 | 8.824 | 37.255 | 1,544,064 | 0.297355 |
| Qwen/Qwen3-8B | animals | 128 | 0 | 28 | 0.000 | 0.003 | — | 16.062 | 68.135 | 83.938 | 6.234 | 56.608 | 4,769,920 | 0.687930 |
| Qwen/Qwen3-8B | animals | 128 | 0.1 | 28 | 0.000 | 0.008 | — | 13.368 | 78.406 | 86.632 | 3.226 | 50.372 | 4,619,776 | 0.634191 |
| Qwen/Qwen3-8B | synthetic | 32 | 0 | 28 | 0.000 | 0.000 | — | 3.571 | 78.571 | 96.429 | 9.091 | 3.571 | 1,087,488 | 0.207596 |
| Qwen/Qwen3-8B | synthetic | 32 | 0.1 | 28 | 0.000 | 0.003 | — | 7.143 | 85.714 | 92.857 | 9.091 | 0.000 | 1,028,352 | 0.184160 |
| Qwen/Qwen3-8B | synthetic | 128 | 0 | 28 | 0.000 | 0.000 | — | 14.286 | 67.857 | 85.714 | 1.010 | 74.747 | 5,479,936 | 0.854564 |
| Qwen/Qwen3-8B | synthetic | 128 | 0.1 | 28 | 0.000 | 0.001 | — | 3.571 | 67.857 | 96.429 | 0.254 | 90.076 | 5,482,496 | 0.839507 |
| Qwen/Qwen3-8B | synthetic | 256 | 0 | 28 | 0.000 | 0.000 | — | 0.000 | 36.240 | 100.000 | 0.272 | 95.380 | 5,365,376 | 0.802240 |
| Qwen/Qwen3-8B | synthetic | 256 | 0.1 | 28 | 0.000 | 0.000 | — | 0.000 | 43.324 | 100.000 | 0.272 | 95.380 | 5,496,832 | 0.781229 |
| openai/gpt-oss-120b | animals | 32 | 0 | 5 | 0.000 | 0.067 | — | 0.000 | 0.000 | 92.000 | 81.818 | 76.364 | 57,600 | 0.028878 |
| openai/gpt-oss-120b | animals | 32 | 0.1 | 5 | 0.000 | 0.008 | — | 0.000 | 0.000 | 98.000 | 70.909 | 61.818 | 62,464 | 0.025432 |
| openai/gpt-oss-120b | synthetic | 32 | 0 | 5 | 0.000 | 0.098 | — | 2.000 | 2.000 | 84.000 | 69.091 | 67.273 | 40,704 | 0.026043 |
| openai/gpt-oss-120b | synthetic | 32 | 0.1 | 5 | 0.000 | 0.057 | — | 0.000 | 0.000 | 88.000 | 80.000 | 80.000 | 43,392 | 0.026154 |

All confidence intervals, token counts, predicate lengths, and re-ask denominators are in summary.json. A constant all-loss or all-win sample has a degenerate percentile-bootstrap interval; this does not establish a zero or perfect population rate. The reference has five games per cell and a 512-token cap including reasoning.
