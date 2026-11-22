# Full game transcripts

Four N=32 animal cases, each with the raw policy and all three trained policies. Within each noise level, take the lowest numeric case index where raw wins and all trained policies lose, then the lowest where raw loses and all trained policies win. The selection illustrates wins and losses for every policy.

Each case includes the common opening prompt and every untrimmed decoded action and reply. The target, score, and flip annotations belong to the reader. The archives retain the original model text and token data.

| Case | Noise | Raw | A11 | A23 | B41 |
| --- | ---: | --- | --- | --- | --- |
| [paid-v1/animals/32/1/p0](animals-n32-case-1-truthful.md) | 0 | Win | Loss | Loss | Loss |
| [paid-v1/animals/32/5/p0](animals-n32-case-5-truthful.md) | 0 | Loss | Win | Win | Win |
| [paid-v1/animals/32/4/p0.1](animals-n32-case-4-noisy.md) | 0.1 | Win | Loss | Loss | Loss |
| [paid-v1/animals/32/5/p0.1](animals-n32-case-5-noisy.md) | 0.1 | Loss | Win | Win | Win |
