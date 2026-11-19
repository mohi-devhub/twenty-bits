# Question-budget visibility audit

The initial user settings state the fixed maximum and final-guess rule. Each later user message contains YES/NO/INVALID plus candidate feedback, with no used/remaining counter or exhaustion notice. All 110 attempts had the maximum in history; none had an explicit per-turn remaining budget. The model could infer usage from played actions in history. No prompt was changed.

At N=128 the initial user settings are exactly:

```text
Answer flip probability: 0.00, independently each question. Maximum questions: 14. After the last answer, make one final guess; another question loses. Begin.
```

The rules also say: `You must make a guess after the last allowed answer.`

| Before the 110 post-budget ASK actions | Stated | Not stated |
| --- | ---: | ---: |
| Fixed maximum in conversation history | 110 | 0 |
| Current remaining question count | 0 | 110 |
| Explicit budget-exhausted notice | 0 | 110 |

The categories overlap: a fixed maximum was visible in every case, while a dynamic remaining count was absent in every case. All 110 native prompt token sequences match the saved rollout inputs. This audit changes neither prompts nor scores. It does not establish why a model kept asking.

[Every case and exact latest feedback](A23_budget_visibility.json).
