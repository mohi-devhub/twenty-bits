# Tinker platform check

Checked on 2026-11-17. No Tinker service requests, training, or inference were made. Public documentation and GitHub source inspection cost $0 in Tinker charges.

## Reuse the existing recipe

Both requested paths exist in the [official cookbook](https://github.com/thinking-machines-lab/tinker-cookbook/tree/6c081121b90dbc290b4550eb9fd9f646f8e4960a/tinker_cookbook/recipes/multiplayer_rl):

- `tinker_cookbook/recipes/multiplayer_rl/`
- `tinker_cookbook/recipes/multiplayer_rl/twenty_questions/`

Inspected cookbook commit: `6c081121b90dbc290b4550eb9fd9f646f8e4960a`, released 2026-11-17. The [recipe environment](https://github.com/thinking-machines-lab/tinker-cookbook/blob/6c081121b90dbc290b4550eb9fd9f646f8e4960a/tinker_cookbook/recipes/multiplayer_rl/twenty_questions/env.py) already maintains the player history, renders observations, and creates groups sharing a target. It calls an LLM answerer, accepts free-form questions, uses 20 turns, and permits another attempt after a wrong guess. Those rules differ from this project's rules.

The integration plan is:

| Reused code | Twenty Bits addition or replacement |
| --- | --- |
| `Env.initial_observation`, `Env.step`, `StepResult` and the recipe's conversation lifecycle | A table-backed environment implementing these interfaces, with exact parser and answerer, seeded flips, INVALID handling, and terminal wrong guesses |
| `TwentyQuestionsEnvGroupBuilder` and dataset-builder pattern | Same candidate table and target for a group's games, with separate reproducible noise streams |
| `rl.rollouts.do_single_rollout` and `do_group_rollout` | Per-turn exact information metrics and reasoning/action token logs |
| `rl.data_processing.trajectory_to_data` and `assemble_training_data` | Existing masks and sampled log-probabilities, plus explicit group-standardized advantages |
| Cookbook renderers, tokenizer helpers, and completers | Model-correct chat templates, supported reasoning channels, and ledger-protected sampling |
| RL training operations and checkpoint helpers | Budget-protected forward/backward, optimizer, sampling, metadata, and checkpoint operations |

The stock environment cannot provide exact predicates by wrapping only its answerer. Its action parsing, reward, termination, prompt, dataset split, and metrics must also change. Reuse the interface and rollout code; adapt the environment rather than launch the stock recipe.

An important mismatch: [upstream `compute_advantages`](https://github.com/thinking-machines-lab/tinker-cookbook/blob/6c081121b90dbc290b4550eb9fd9f646f8e4960a/tinker_cookbook/rl/data_processing.py#L24) subtracts the group mean, but does not divide by the group standard deviation. Phase 3 needs the requested `(R - mean) / (std + epsilon)`, with zero advantages for constant groups, before assembling data. Pin the upstream revision and test this adapter. Do not call upstream defaults GRPO without checking their behavior.

Phase 0 implements only budget support. No environment or training adapter is claimed as implemented yet. Never run the recipe's defaults: they include a billable LLM answerer and a much larger workload than this budget.

## Model recommendation

The main recommendation is `Qwen/Qwen3-8B`, the chat-tuned hybrid model, not the retired `Qwen3-8B-Base`. It fits the requested 4B to 8B range, supports thinking, and costs less than the listed 4B replacement. The larger zero-shot-only reference is `openai/gpt-oss-120b`. It is a mixture-of-experts model, so total parameter count is not active compute or a controlled model-size comparison.

| Model | Context | Prefill | Cached prefill | Output | Training |
| --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen3-8B` | 32K | $0.195 | $0.039 | $0.60 | $0.44 |
| `openai/gpt-oss-120b` | 32K | $0.33 | $0.066 | $0.84 | $0.737 |

Rates are USD per million tokens from the [public rate card](https://tinker-docs.thinkingmachines.ai/tinker/models.json). They are planning inputs, not guaranteed future rates. Before Phase 2, tokenize the real longest prompts, refresh rates, and freeze the renderer and token caps. Thinking tokens count toward output billing. Log only visible reasoning tokens; never infer hidden reasoning from latency.

## Published inventory and an inconsistency

The [saved catalog](research/tinker-models-2026-11-17.json) lists 39 exact IDs, representing 26 model names before context variants. Three listed IDs are already retired according to the [deprecations page](https://tinker-docs.thinkingmachines.ai/tinker/model-deprecations/). That leaves 36 entries not marked retired, not 39 verified available models. Account-specific availability still needs a capabilities response.

| Exact published Tinker ID | Context | Retired per deprecations page |
| --- | --- | --- |
| `thinkingmachines/Inkling-2-Small` | 64K | |
| `thinkingmachines/Inkling-2-Small:peft:262144` | 256K | |
| `thinkingmachines/Inkling` | 64K | |
| `thinkingmachines/Inkling:peft:262144` | 256K | |
| `thinkingmachines/Inkling-Small` | 64K | |
| `thinkingmachines/Inkling-Small:peft:262144` | 256K | |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16` | 64K | |
| `nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16:peft:262144` | 256K | |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | 64K | |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16:peft:262144` | 256K | |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16` | 64K | |
| `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16:peft:262144` | 256K | |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | 64K | |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16:peft:262144` | 256K | |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | 64K | 2026-10-23 |
| `zai-org/GLM-5.3:peft:262144` | 256K | |
| `zai-org/GLM-5.3-Flash:peft:262144` | 256K | |
| `moonshotai/Kimi-K3.1-Pro:peft:262144` | 256K | |
| `moonshotai/Kimi-K2.6` | 32K | |
| `moonshotai/Kimi-K2.6:peft:131072` | 128K | |
| `Qwen/Qwen3.8-27B` | 64K | |
| `Qwen/Qwen3.8-27B:peft:262144` | 256K | |
| `Qwen/Qwen3.6-35B-A3B` | 64K | |
| `Qwen/Qwen3.6-35B-A3B:peft:262144` | 256K | |
| `Qwen/Qwen3.6-27B` | 64K | 2026-10-23 |
| `Qwen/Qwen3.5-397B-A17B` | 64K | |
| `Qwen/Qwen3.5-397B-A17B:peft:262144` | 256K | |
| `Qwen/Qwen3.5-35B-A3B-Base` | 64K | |
| `Qwen/Qwen3.5-9B` | 64K | |
| `Qwen/Qwen3.5-9B-Base` | 64K | |
| `Qwen/Qwen3.5-4B` | 64K | |
| `Qwen/Qwen3.5-4B:peft:262144` | 256K | |
| `Qwen/Qwen3-8B` | 32K | |
| `openai/gpt-oss-120b` | 32K | |
| `openai/gpt-oss-120b:peft:131072` | 128K | |
| `openai/gpt-oss-20b` | 32K | |
| `deepseek-ai/DeepSeek-V4.1-Flash:peft:262144` | 256K | |
| `deepseek-ai/DeepSeek-V4.1-Flash-1017:peft:262144` | 256K | |
| `deepseek-ai/DeepSeek-V3.1` | 32K | 2026-10-23 |

`Qwen3-4B-Instruct-2507` retired on 2026-06-12. Its suggested replacement is `Qwen/Qwen3.5-4B` with thinking disabled. The published `Qwen/Qwen3-8B` recommendation above remains listed and is not on the retirement list.

The local Python environment has neither the Tinker SDK nor `TINKER_API_KEY`. The standard stored-credential file is absent too. No account access, balances, storage plan, or server capabilities were verified. The authenticated check before spending is `tinker.RestClient().get_server_capabilities().result().supported_models`, wrapped in a zero-dollar ledger operation. Public source inspection is complete; live account verification is pending credentials.

## A 408 is a pending future

Inspected SDK commit: `1969e0b4ff462717f154347b0c1094269426514d`, dated 2026-11-17. In [`api_future_impl.py`](https://github.com/thinking-machines-lab/tinker/blob/1969e0b4ff462717f154347b0c1094269426514d/src/tinker/lib/api_future_impl.py#L160), HTTP 408 is classified as retryable pending retrieval. The REST fetch passes `request_id=self.request_id` again.

Persist the original ID as soon as it is exposed. Re-poll that same future or let the SDK do it. A `retrieve_future` 408 does not authorize another `sample`, `forward_backward`, or optimizer submission. Keep the original cost hold. Do not use a rollout retry policy to restart an episode because Tinker is slow.

The ledger tests cover retaining holds and rejecting replacement IDs. They do not exercise a live SDK future. Phase 2 must connect the guard to the pinned SDK and test pending responses with a mocked transport before any paid sampling.

## Billing reconciliation

The inspected SDK exposes hourly [billing usage events](https://github.com/thinking-machines-lab/tinker/blob/1969e0b4ff462717f154347b0c1094269426514d/src/tinker/types/billing_usage_response.py) with session attribution, token categories, cache flags, and costs that can be unavailable or provisional. Missing cost is not zero. Save raw usage snapshots and keep holds until the attributable gross cost is reconciled. Do not subtract unrelated account spending or count credits as permission to exceed $30 of project usage.

[Checkpoint storage](https://tinker-docs.thinkingmachines.ai/administration/checkpoint-storage-pricing/) is free within organization limits on the free plan. Paid storage bills all stored data. Inspect the plan and capacity before saving, use bounded lifetimes, and reserve storage liability if applicable. The budget scenarios assume free-plan headroom; that assumption has not been verified.

## Phase 1 update

The offline engine and baselines now exist. PAID_PLANS.md replaces the old paid-grid proposal. Its tokenizer counts use native HF chat templates at pinned revisions; the cookbook adapter and its token-parity check are still pending Phase 2. No SDK or Tinker service operation was used in Phase 1.

Public pricing was rechecked on 2026-11-18. The three costed models have unchanged rates, recorded in research/rate_recheck.json. Caching is supported for shared prefixes within a sampling client, but no cache hit or authenticated availability has been observed for this project. Both paid forecasts assume no cache savings.

## Phase 2 update

On 2026-11-18 the user approved a $50 cap and provided a local ignored credential. Authenticated capabilities listed 38 models, including Qwen3-8B and gpt-oss-120b with 32,768-token contexts and sampling enabled. [The saved capabilities](research/phase2_capabilities.json) and [verified rates](research/phase2_rates.json) replace the earlier unverified availability assumptions.

The bridge reuses cookbook commit 6c081121b90dbc290b4550eb9fd9f646f8e4960a and SDK 0.39.1. Cookbook/native token parity passed for all 300 approved initial prompts and 259 histories before sampling. An independent pinned environment reproduced those token hashes. The exact replay later reconstructed all 3,779 submitted token sequences and sampling settings. [Verification](results/phase2/verification.json) records that check.

Live responses report cache hits in every evaluated cell. Counts, fractions, token costs, and CIs appear in [the gate report](PHASE2.md) and [cell data](results/phase2/summary.json). The output-length assumption missed badly; the next pilot is priced using observed lengths with explicit sensitivity bounds.

The adapter had omitted the native sampling-backpressure header. Matching the SDK request fields and header resolved the misleading outdated-SDK rejection. Five originals stay orphaned, possibly billed; their $0.007195 holds stay until billing resolves them, and their outputs are never used. New sampling future IDs are persisted before HTTP dispatch and verified against receipts. A 408 still re-polls the same request. [The incident record](research/phase2_incident.json) includes the approved replacements and local restart repair.

The final billing snapshot currently contains no attributable rows and may lag usage by hours. It is not evidence of free sampling and does not release orphan holds. The ledger records observed token usage at the verified published rates, with invoice reconciliation pending. No storage plan was changed and no training or checkpoint save occurred.
