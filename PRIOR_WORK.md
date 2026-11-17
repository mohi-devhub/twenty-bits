# Prior work

Checked on 2026-11-17. These are primary papers, author releases, and publisher pages. This is a targeted literature check, not a systematic review.

## Work closest to Twenty Bits

### Paprika, Tajwar et al., ICML 2025

Did: [Training a Generally Curious Agent](https://proceedings.mlr.press/v267/tajwar25a.html) trains on synthetic multi-turn tasks including Twenty Questions, using successful-trajectory SFT followed by multi-turn preference optimization and a curriculum. It tests transfer to unseen tasks. The [paper's optimization section](https://arxiv.org/html/2502.17543#S3.SS3) distinguishes this from online RL.

Difference: Twenty Bits proposes online grouped RL on animals alone, an exact scripted answerer, and exact information measurements without rewarding information gain. Training 20Q players, curricula, and exploration transfer are already done.

### Bertolazzi et al., INLG 2023

Did: [ChatGPT's Information Seeking Strategy: Insights from the 20-Questions Game](https://aclanthology.org/2023.inlg-main.11/) measures ChatGPT's narrowing, informativeness, and stopping in hierarchical candidate spaces built from feature norms. Explicitly tracking remaining candidates improves performance.

Difference: Twenty Bits would measure changes caused by RL against known table posteriors, including noisy answers. Comparing questions to informative splits is already done.

### Zhang, Lu, and Jaitly, ACL 2024

Did: [Probing the Multi-turn Planning Capabilities of LLMs via 20 Question Games](https://aclanthology.org/2024.acl-long.82/) introduces an entity-deduction evaluation, studies behavior cloning and domain generalization, and improves Vicuna through reinforcement learning from gameplay.

Difference: Twenty Bits makes every answer and posterior exact, then measures information efficiency and noise recovery separately from success. An RL-trained LLM playing 20Q is already done, including in this paper, not only Paprika.

### Mazzaccara, Testoni, and Bernardi, Findings of EMNLP 2024

Did: [Learning to Ask Informative Questions: Enhancing LLMs with Preference Optimization and Expected Information Gain](https://aclanthology.org/2024.findings-emnlp.291/) samples Llama 2-Chat 7B questions, builds high-EIG versus low-EIG preference pairs, and uses DPO to improve informativeness, including in other domains.

Difference: Twenty Bits keeps EIG out of training rewards and asks whether success and question cost alone produce information-efficient behavior. Both EIG-based training and cross-domain improvement are already done.

### Abdulhai et al., 2023 preprint, ICML 2025

Did: [LMRL Gym](https://arxiv.org/abs/2311.18232), with [released task code](https://github.com/abdulhaim/LMRL-Gym), benchmarks multi-turn language-model RL. Its Twenty Questions task uses an LLM oracle and a penalty for unsuccessful questions.

Difference: Twenty Bits replaces uncertain oracle judgments with table predicates and exact posteriors. Penalizing questions to encourage efficient 20Q play is already done.

## Information gain and related evaluations

### Hu et al., 2024

Did: [Uncertainty of Thoughts](https://arxiv.org/abs/2402.03271) uses simulated future conversations and information-gain-based search rewards to select questions, evaluating 20Q, diagnosis, and troubleshooting.

Difference: Twenty Bits would train the policy weights and measure EIG exactly afterward. Choosing questions through information-gain-guided lookahead is already done.

### Grand et al., CogSci 2024

Did: [Loose LIPS Sink Ships](https://arxiv.org/abs/2402.19471) generates natural-language Battleship questions with LLMs, translates them to symbolic programs, and selects informative questions through expected information gain.

Difference: Twenty Bits directly outputs predicates and learns from game rewards. Executable question meanings combined with EIG are already done.

### Choudhury et al., 2025 preprint, ICLR 2026

Did: [BED-LLM](https://arxiv.org/abs/2508.21184) uses sequential Bayesian experimental design to maximize estimated EIG from LLM predictive distributions, including 20Q and preference elicitation.

Difference: Twenty Bits computes beliefs from a finite table and a known answer channel. EIG-based adaptive 20Q question selection is already done.

### Dutta, Ramachandran, and Sra, 2026 preprint

Did: [Active Inference as Context Acquisition for AI Agents](https://arxiv.org/abs/2608.19202) includes Optimal Question Asking with exact posteriors, a dynamic-programming reference, candidate sets of 25 to 300, and synthetic attribute-table scaling.

Difference: Twenty Bits would measure policy learning under a success-only objective plus costs and real seeded answer flips. Exact posteriors, synthetic attributes, candidate-size scaling, and comparison to an optimal reference are already done.

### Li, Chang, and Garcia, 2026 preprint

Did: [Learning What to Ask and What to Believe](https://arxiv.org/abs/2611.01245) distills a Bayesian EIG teacher into an 8B language model with structured belief traces. It tests transfer across task families and reports a failure to transfer.

Difference: Twenty Bits proposes outcome-based RL rather than Bayesian demonstrations. Learning information-seeking in a small model and testing whether it transfers are already done. This recent preprint also cautions against assuming that success within a task implies a general search skill.

### Huang et al., 2026 preprint

Did: [Do LLMs Know What to Ask and When?](https://arxiv.org/abs/2608.14808) introduces MT-InfoSeek, measuring what models ask, query order, sufficiency of acquired information, and when they stop across several domains.

Difference: Twenty Bits would isolate binary search over a visible table and use entropy reduction as a continuous question-level measure. Evaluating information acquisition separately from final-answer correctness is already done.

### Cui, Ling, and Ng, 2026 preprint

Did: [Game of Thought](https://arxiv.org/abs/2602.01708) formulates adversarial Twenty Questions as Strategic Language Search and uses game-theoretic strategies to improve worst-case performance.

Difference: Twenty Bits uses independent 10% answer flips and studies learned checking behavior. Adversarial robustness in information seeking is already studied, but adversarial target selection is a different noise model from independent lies.

### Jedynak, Frazier, and Sznitman, Journal of Applied Probability 2012

Did: [Twenty Questions with Noise: Bayes Optimal Policies for Entropy Loss](https://people.orie.cornell.edu/pfrazier/pub/2011_JedynakFrazierSznitman_20questions.pdf) analyzes Bayesian question selection with a known noisy oracle and entropy loss.

Difference: Twenty Bits asks whether a language model learns related behavior from rewards. Noisy 20Q, Bayesian updating, and posterior bisection are established theory.

## What claim remains useful

The defensible project is a small, reproducible measurement study: can outcome-based RL improve exact information gain, noise recovery, and table-search transfer under one fixed grammar? It is not a new game, a new information metric, or the first application of RL to 20Q.

EIG in bits is a change of logarithm base from entropy in nats. Calling the same quantity "bits per question" does not make it new. The win-only ratio `log2(N) / questions` is a different statistic and needs the cautions in [DESIGN_NOTES.md](DESIGN_NOTES.md).

The literature check did not establish that the exact combination of outcome-only grouped RL, independent 10% lies, exact table metrics, and relabeled synthetic transfer has already been run. Absence from this search is not evidence of novelty.

## Proposed replacements for overlapping twists

These are proposals for the next gate, not changes to the experiment.

| Overlapping idea | Proposed sharper question |
| --- | --- |
| RL makes an LLM play 20Q | How much does outcome-only RL close the EIG gap to an exact executable reference? |
| EIG training makes questions informative | Does EIG improve when it is never used as a training signal? |
| Strategy transfers across semantic domains | Does performance survive new random tables, new names, and shuffled row and column order? |
| Robust information seeking | Does noisy training selectively increase checks after low-probability answers, compared with matched ordinary answers? |
| Synthetic table search against an optimum | Measure both information efficiency and the output-token cost of item-enumerating predicates. |

Keep legal `item == X` and long disjunctions visible in the audit. Do not silently ban them or claim attribute reasoning if enumeration explains the result. If enumeration dominates, a separately approved grammar or token-cost experiment can test the mechanism.
