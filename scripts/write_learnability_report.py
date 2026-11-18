"""Write the diagnosis and probe gate from saved numbers, without service calls."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
            *["| " + " | ".join(map(str, row)) + " |" for row in rows],
        ]
    )


def pct(x):
    return f"{100 * x:.1f}%"


def cell_name(cell):
    return [cell["model"].split("/")[-1], cell["domain"], cell["n"], cell["noise"]]


def main():
    diagnosis = json.loads((ROOT / "results/diagnosis/phase2.json").read_text())
    probe = json.loads((ROOT / "results/learnability_probe/summary.json").read_text())
    random_play = json.loads((ROOT / "results/diagnosis/random_valid.json").read_text())
    warm = json.loads((ROOT / "research/format_warmstart_price.json").read_text())
    price = json.loads((ROOT / "research/learnability_forecast.json").read_text())
    timing = json.loads(
        (ROOT / "results/learnability_probe/recovery_timing.json").read_text()
    )
    cells = diagnosis["cells"]
    turn_table = table(
        [
            "Model",
            "Domain",
            "N",
            "p",
            "Turns",
            "Valid ASK",
            "Valid GUESS",
            "INVALID",
            "Other",
            "Truncated",
            "Empty",
        ],
        [
            cell_name(c)
            + [c["turns"]]
            + [
                c["outcomes"].get(k, 0)
                for k in [
                    "valid_ASK",
                    "valid_GUESS",
                    "INVALID",
                    "other",
                    "truncated",
                    "empty",
                ]
            ]
            for c in cells
        ],
    )
    categories = [
        "column_code_as_attribute",
        "unknown_attribute",
        "name_outside_candidates",
        "missing_close_parenthesis",
        "missing_item_equality",
        "missing_expression",
        "illegal_character_or_unclosed_quote",
        "action_format",
        "trailing_tokens",
    ]
    error_table = table(
        [
            "Model",
            "Domain",
            "N",
            "p",
            "Code",
            "Unknown attr",
            "Unknown name",
            "Missing )",
            "Missing ==",
            "Missing expr",
            "Bad text/quote",
            "Action format",
            "Trailing",
        ],
        [
            cell_name(c) + [c["parse_errors"].get(k, 0) for k in categories]
            for c in cells
        ],
    )
    end_table = table(
        [
            "Model",
            "Domain",
            "N",
            "p",
            "Games",
            "Budget/no guess",
            "Wrong guess",
            "Context limit",
            "Invalid-heavy",
            "Never guessed",
        ],
        [
            cell_name(c)
            + [
                c["games"],
                c["endings"].get("budget_exhausted_without_guess", 0),
                c["endings"].get("wrong_guess", 0),
                c["endings"].get("context_limit", 0),
                c["overlapping_game_flags"]["invalid_heavy_at_least_half_questions"],
                c["overlapping_game_flags"]["never_guessed"],
            ]
            for c in cells
        ],
    )
    bridge_keys = [
        "forecast_usd",
        "turn_count_change_usd",
        "input_length_change_usd",
        "output_length_change_usd",
        "cache_credit_usd",
        "rounding_usd",
    ]
    bridge_table = table(
        ["USD component", "Qwen3-8B", "gpt-oss-120b", "Total"],
        [
            [
                key,
                *[f"{Decimal(c['bridge'][key]):+.6f}" for c in diagnosis["costs"]],
                f"{sum(Decimal(c['bridge'][key]) for c in diagnosis['costs']):+.6f}",
            ]
            for key in bridge_keys
        ]
        + [
            [
                "Recorded usage",
                *[c["actual_usd"] for c in diagnosis["costs"]],
                "5.793225",
            ]
        ],
    )
    token_table = table(
        [
            "Model",
            "Turns forecast / used",
            "Input forecast / used",
            "Output forecast / used",
            "Cache-hit tokens",
            "INVALID turns / cost",
        ],
        [
            [
                c["model"].split("/")[-1],
                f"{c['forecast_turns']:,} / {c['actual_turns']:,}",
                f"{c['forecast_input_tokens']:,} / {c['actual_input_tokens']:,}",
                f"{c['forecast_output_tokens']:,} / {c['actual_output_tokens']:,}",
                f"{c['prompt_cache_hit_tokens']:,}",
                f"{c['invalid_turns']:,} / ${c['invalid_turn_cost_usd']}",
            ]
            for c in diagnosis["costs"]
        ],
    )
    all_games = [
        json.loads(line)
        for line in gzip.open(ROOT / "results/phase2/games.jsonl.gz", "rt")
    ]
    ref = [g for g in all_games if g["model"] != "Qwen/Qwen3-8B"]
    reasoning = sum(g["reasoning_tokens"] for g in ref)
    output = sum(g["output_tokens"] for g in ref)
    text = f"""# Phase 2 failure diagnosis

The saved games contain a grammar and termination failure before there is a useful search-policy comparison. Qwen made three guesses, all wrong, in 280 games. It produced 447 valid questions, all with item equalities. The reference never guessed in 20 games. This diagnosis makes zero service calls and reads only accepted, saved Phase 2 outputs. The five older orphaned outputs remain excluded.

## Every generated turn

Valid ASK, valid GUESS, INVALID and other partition generated turns. A valid GUESS names a listed candidate with one line, whether or not it is correct. Other includes a further ASK in the final-guess slot. Truncated and empty overlap the partition. An action can be both truncated and INVALID. Empty means no decoded action, not no generated reasoning. A second mutually exclusive partition with truncation priority is in [phase2.json](results/diagnosis/phase2.json).

{turn_table}

## Parser and validation errors

Each INVALID receives one category based on its actual error. The parser reports the error it encounters; a longer expression can contain additional defects. Code means a table column code used where a full attribute name is required. Unknown name means a name outside the current table. Bad text or quote includes a generated token outside the grammar and cut-off quoted names. Truncation flags above prevent interpreting all such errors as independent grammar failures.

{error_table}

## How games end

Budget/no guess, wrong guess and context limit are exclusive terminal causes. Context limit takes precedence when the next rendered prompt plus the unchanged output allowance cannot fit. Invalid-heavy means at least half the counted questions were INVALID. Invalid-heavy and never-guessed are overlapping behavioral flags, not extra terminal causes. Across both models, 165 games ended at the budget without a guess, three ended with a wrong guess, and 132 hit the context limit. 297 of 300 never guessed.

{end_table}

## The 311 questions below 1e-12 EIG

Eight questions name only already-eliminated items. Zero name an item outside the candidate table. The other 303 consist of 82 predicates with an already-implied answer after elimination, 220 predicates constant on the entire table, and one with a nearly certain noisy posterior. Unknown names produce INVALID instead and are counted in the error table. The eight eliminated-item questions and 82 implied-answer questions together account for 90 predicates that became constant after noiseless elimination. Constant-table cases include tautological name lists and predicates false everywhere. The one near-certain case is a numerical threshold case, not an exact logical constant. [All 311 classifications](results/diagnosis/phase2.json) include both the requested name-based grouping and the semantic cause, table split, posterior mass, and count of named eliminated items.

## Why the reference also loses

Of its 220 turns, 157 hit the 512-token cap while still in the analysis channel. All 157 decode to an empty action. It generated {reasoning:,} visible reasoning tokens out of {output:,} total generated tokens. Only 19 questions were valid; 35 more used column codes as unknown attributes. The 157 empty turns include final-slot failures, so the parser's action-format count is smaller. It made no GUESS. This is an analysis-budget and format failure. It does not establish that a sufficiently budgeted reference cannot solve the game. No reference rerun is authorized or charged here.

## Cost reconciles to token usage

Actual recorded usage is 1.958 times the $2.95805922 forecast. The forecast allowed full question budgets but only 64 Qwen output tokens per turn, 128 reference tokens, and 32 history-overhead tokens. It credited no cache hits. Actual Qwen outputs averaged about 1,488 tokens per turn. Their repeated inclusion in later contexts raised uncached input work as well as output work.

The bridge changes turn count at forecast lengths, then substitutes observed input lengths, observed output lengths, cache hits, and per-call upward rounding. The order is fixed and all rows add exactly before display rounding. Input changes include different initial prefixes and the much larger generated histories.

{bridge_table}

{token_table}

INVALID turns cost $5.191835, or 89.6% of the total. That is a subset of actual spend, not another additive explanation. Their later history also costs input tokens, already included in the input-length and cache rows. The $0.007195 in old orphan holds is separate. These are gross usage charges from saved token counts and rates, not finalized invoices. [Rate card](https://tinker-docs.thinkingmachines.ai/tinker/models.json).

## Three complete transcripts

These are deterministic category examples from saved games, not a performance sample. They include the full public table, settings, every raw generated response, decoded actions, and all answers. Targets are revealed only in the diagnostic files. No response text is shortened.

- [Qwen malformed and truncated questions](results/diagnosis/transcripts/qwen-malformed.md): animals N=32, index 0, p=0.
- [Qwen legal zero-information repetition](results/diagnosis/transcripts/qwen-zero-information.md): animals N=32, index 1, p=0.
- [Reference analysis truncation](results/diagnosis/transcripts/reference-analysis-only.md): animals N=32, index 0, p=0.

Reproduce with `.venv/bin/python scripts/diagnose_phase2.py`. The [source hash, exact bridge, partitions and categories](results/diagnosis/phase2.json) and [turn CSV](results/diagnosis/turns.csv) are saved.
"""
    (ROOT / "DIAGNOSIS.md").write_text(text)

    observed = table(
        [
            "N",
            "Games",
            "Valid turns [game-bootstrap CI]",
            "Wins [Wilson CI]",
            "Usage USD/game",
            "EIG/Q",
            "Questions/win",
            "Truncated turns",
        ],
        [
            [
                c["n"],
                c["games"],
                f"{c['valid_turns']}/{c['turns']} = {pct(c['valid_turn_rate'])} [{', '.join(pct(x) for x in c['valid_turn_ci95_game_bootstrap'])}]",
                f"{c['wins']}/{c['games']} [{', '.join(pct(x) for x in c['win_wilson_ci95'])}]",
                f"{c['cost_per_complete_game_usd']:.8f}",
                f"{c['metrics']['eig_per_question']:.6f}",
                f"{c['metrics']['questions_per_win']:.2f}"
                if c["wins"]
                else "undefined",
                pct(c["truncation_rate"]),
            ]
            for c in probe["cells"]
        ],
    )
    random_rows = []
    for c in random_play["cells"]:
        if c["noise"]:
            continue
        noisy = next(
            x for x in random_play["cells"] if x["n"] == c["n"] and x["noise"] == 0.1
        )
        random_rows.append(
            [
                c["n"],
                f"{pct(c['win_rate'])} [{', '.join(pct(x) for x in c['win_ci95_clustered'])}]",
                pct(c["singleton_wins"] / c["games"]),
                pct(noisy["win_rate"]),
                pct(c["mixed_win_groups"]),
                pct(c["nonzero_return_variance_groups"]),
            ]
        )
    random_table = table(
        [
            "N",
            "Random-valid win p=0 [95% CI]",
            "Win with singleton p=0",
            "Win p=.10",
            "Mixed-win groups p=0",
            "Nonzero-return groups p=0",
        ],
        random_rows,
    )
    times = table(
        [
            "Request suffix",
            "Receipt saved",
            "Dispatch to collection attempt",
            "Dispatch to terminal recovery reply",
            "Dispatch to explicit inspection",
            "Result",
        ],
        [
            [
                t["request_id"].rsplit(":", 1)[-1],
                t["receipt_saved"],
                f"{t['seconds_to_first_collection_attempt']:.2f}s",
                f"{t['seconds_to_earliest_terminal_recovery_reply'] / 60:.2f} min"
                if t["seconds_to_earliest_terminal_recovery_reply"] is not None
                else "no terminal body",
                f"{t['seconds_to_explicit_inspection'] / 60:.2f} min",
                "404"
                if t["inspection_result"].get("http_status") == 404
                else "response expired",
            ]
            for t in timing["futures"]
        ],
    )
    pc = price["pilot"]["measured_token_proxy"]
    stress = price["pilot"]["full_output_cap_stress"]
    cost_table = table(
        [
            "Proposed work",
            "Measured-token proxy with 1.5x margin",
            "2048-output scenario with 1.5x margin",
        ],
        [
            [
                "16-update A pilot without SFT",
                f"${pc['without_sft_with_margin_usd']:.2f}",
                f"${stress['without_sft_with_margin_usd']:.2f}",
            ],
            [
                "Format SFT, qualification, then 16-update A pilot",
                f"${pc['with_sft_with_margin_usd']:.2f}",
                f"${stress['with_sft_with_margin_usd']:.2f}",
            ],
            [
                "Stop after SFT and qualification",
                f"${pc['sft_qualification_only_with_margin_usd']:.2f}",
                f"${stress['sft_qualification_only_with_margin_usd']:.2f}",
            ],
            [
                "Stop after four RL updates, including SFT",
                f"${pc['abort_after_four_updates_with_sft_and_margin_usd']:.2f}",
                f"${stress['abort_after_four_updates_with_sft_and_margin_usd']:.2f}",
            ],
            [
                "One full 280-game endpoint",
                f"${price['full_eval_280_games_with_margin_usd']:.2f}",
                f"${price['full_eval_280_full_cap_stress_with_margin_usd']:.2f}",
            ],
        ],
    )
    results = f"""# Learnability gate

Completed 2026-11-18. The 32-game prompt-only probe is complete. No SFT, RL, optimizer update, or extra reference evaluation ran. Training is not approved.

The prompt change gives Qwen one win at N=8 and none at N=16. Valid-turn rates remain {pct(probe["cells"][0]["valid_turn_rate"])} and {pct(probe["cells"][1]["valid_turn_rate"])}. Most invalid questions still use table column codes instead of full attribute names. Recommend a short grammar warm start, followed by a qualification check, before any RL. Prompt and size both differ from Phase 2, so the probe is not a controlled estimate of the prompt's effect.

## What the probe actually ran

Qwen3-8B, thinking disabled, 2,048 output tokens, temperature 0.7, top-p 1, top-k disabled, p=0. Sixteen training-pool games each at N=8 and N=16 use seed 20261118 and independent generation seeds per turn. The public table, game rules, grammar, reward and answer-only feedback stay intact. Three worked grammar examples use random attributes, selected without reading column values, target or posterior. No remaining-candidate list is supplied. Frozen prompts, subsets, targets and hashes are unchanged.

Native and cookbook token sequences matched all 32 initial prompts and 224 example-action histories before sampling. Every real probe prompt was checked again before dispatch. Initial prompts and full-cap hold estimates are in the [rendering proof](research/learnability_probe_rendering.json). The complete run's preflight sum of per-call maximum holds was $0.748178. The independent probe cap is $1.50 including active holds. It is checked before each operation as well as the existing $50 project guard.

{observed}

Valid turns include a parsed counted ASK or a one-line GUESS of a listed candidate. A legal wrong guess counts as valid format. Additional ASK output in the final-guess slot is not valid. EIG includes invalid questions and losses. All confidence intervals resample whole games 10,000 times, except the stated Wilson win intervals. The one win is a genuine singleton: the model asked `fur`, `NOT hairless`, `NOT aquatic`, `NOT reptile`, and `NOT white`, then guessed `adult_male_polar_bear`. The exact posterior had one remaining item. That example is a development observation, not a typical-game claim.

Recorded usage is **${probe["cost"]["probe_spent_usd"]}**, plus **${probe["cost"]["probe_held_usd"]} held**. The cost/game values above exclude unresolved originals and include all completed-game turns. [All cell metrics, token counts, intervals and verification](results/learnability_probe/summary.json), [saved games](results/learnability_probe/games.jsonl.gz), and [request metadata](results/learnability_probe/requests.jsonl.gz) are available. Reported cache-hit tokens are response measurements; future forecasts give caching no credit.

## Fix options, from less to more change

**a. Clearer prompt and random grammar examples.** This is the probe already run. The rules explicitly distinguish full attribute names from storage codes. Its spend above is measured. The only model changes were public prompt wording and examples. It did not fix code-as-attribute errors well enough to start RL confidently.

**a plus remaining-candidate feedback.** This is a separate task. After each noiseless answer, a script would reveal posterior support as a list of names. Replaying observed probe actions with that added list gives an estimated **${price["remaining_list_option"]["extra_uncached_usd_32_games"]:.4f} extra input cost for 32 games**, before margin. This is only a token counterfactual; no such policy was sampled, and its changed actions could cost more. At p=.10 all items retain positive posterior mass, so useful posterior-weight feedback would be yet another task change. Do not use this option for the main experiment without a separate decision.

**b. Random-question format SFT.** The offline proposal contains {warm["examples"]} per-turn examples from 128 fresh procedural toy games at N=4 and N=8. Select single attributes uniformly with replacement, independently of target, posterior or EIG. Use varied column prevalences, drop constant columns and enforce unique rows. Include a correct GUESS only at singleton. Ambiguous games contribute questions and no oracle guess. Supervise only the current assistant action, while charging the full context for training. Two passes, batches of 32, give {warm["batches_of_32_examples"]} updates and {warm["full_context_tokens_per_epoch"]:,} full-context tokens per pass. The gradient forecast is ${Decimal(warm["forward_backward_usd"]):.6f}, or **${Decimal(warm["total_with_storage_and_margin_usd"]):.2f} with 1.5x margin and storage**. Dataset construction and supervision-prefix parity are offline; no training ran.

This teaches action syntax, stopping, and table/answer tracking. It supplies no EIG ranking or selected bisection examples. It also supplies a single-attribute action prior, so a pre-RL warm-start control is necessary before attributing that preference to RL. Fresh toy worlds reuse no held-out or frozen rows. However, synthetic SFT exposes the model to random-table identification, so later synthetic transfer must be described as new tables, labels and sizes, rather than a wholly unseen task. An animals-only warm-start variant would preserve the held-out-domain boundary and needs its own priced dataset if preferred. [SFT proposal and exact price](research/format_warmstart_price.json), [proposed examples](experiments/format_warmstart_proposal.jsonl.gz).

**c. Begin at N=4, then N=8.** This changes the training curriculum, with the same `2*ceil(log2 N)` question limit and unchanged reward. It has no separate setup charge. Under the measured token proxy, a group of eight costs the amounts in [learnability_forecast.json](research/learnability_forecast.json), including sampling and full-context gradients. Smaller N improves the reward signal of valid random play; it cannot repair invalid syntax by itself.

## How often random valid play wins

These estimates apply to a grammar-valid random single-attribute policy under options a and b; syntax training alone does not imply the LLM follows that policy. The same table prices the sizes introduced by c. Each size and noise mode has 500 training-pool start states and eight independent policy RNGs per state, 4,000 games. It asks attributes uniformly with replacement. It guesses at singleton, noisy confidence .95, or the budget, using a stable MAP tie break. Intervals resample start states. The singleton column removes wins from lucky final guesses among several candidates. Noisy posterior support never becomes singleton.

{random_table}

The grouped simulation shares each start and seeded noise schedule. It measures the scripted policy, not Qwen's group variance. The paid probe samples one rollout per start, so it cannot directly establish GRPO group statistics. [Simulation data and settings](results/diagnosis/random_valid.json).

## Proposed A-only pilot, not authorization

Use the format warm start only if approved, then check 32 fixed development games from the animals training pool, 16 each at N=4 and N=8. Use a namespace distinct from this probe and the frozen bank. Propose at least 90% valid turns and 8/32 wins before RL. If that qualification fails, stop after SFT and development sampling.

If it passes, run seed 11 with one group of eight games per update. Each group shares one start state. Use N=4 for four updates, N=8 for eight, and N=16 for four: 16 updates and 128 training games. The proposed LoRA rank is 32 and AdamW learning rate is 1e-4 for both stages, with assistant-only loss weights for SFT. Record and freeze the remaining optimizer settings before an approved run. Standardize each group's returns with population SD and explicitly produce zero advantages for a constant-return group. Reward remains +1 win, -0.03/question, -0.1/INVALID. EIG never enters the reward.

Evaluate the same 32 development games at updates 0, 4, 8, 12 and 16. This gives 160 development rollouts and 16 training-curve points. Development results are not confirmatory frozen-eval results. Keep the scheduled endpoint; do not choose a checkpoint by frozen scores.

**Required stop rule:** after four updates, halt if fewer than 25% of groups have nonzero total-return variance, using variance greater than 1e-12. With one group per update, zero of four groups halts; one of four is exactly 25% and passes. Also report mixed-win groups and total wins. Question and invalid costs can make return variance nonzero with zero wins. I recommend an additional zero-wins stop after those 32 training games, subject to approval of the proposed configuration.

{cost_table}

These forecasts use measured output tokens per call, measured native prefixes, the full question budget plus guess, full per-turn contexts for gradients, and no cache discount. N=4 borrows N=8 output lengths. Larger eval sizes borrow N=16 lengths, which is an untested extrapolation. The stress column assumes full 2,048-token outputs until a context-limit loss. It is a scenario rather than a guarantee of successful games. Storage allowances are $0.10 for SFT and $0.10 for the pilot. Use ephemeral fixed-weight sampler copies between updates and at most five named pilot snapshots plus one SFT snapshot, each bounded at 64 GB with a two-hour TTL. Their storage bounds are $0.088889 and $0.017778 at $0.10/GB/month. Download retained weights before expiry. Optimizer-state checkpoints are not included. Reserve storage before any save. Calls still reserve the larger of 1.5x estimated cost and their token-limited maximum.

Endpoint evaluations remain expensive relative to this small pilot. The primary RL control must be the pre-RL policy under the same prompt on the same 280 frozen cases. With SFT, that is the warm-start checkpoint; without SFT, it is the newly prompted raw base. A separate raw-base versus warm-start ablation is optional and costs another full evaluation. Existing Phase 2 scores remain historical and cannot isolate RL under a changed prompt. Leave the bank unchanged and add a separately approved prompt-version hash manifest. Do not start those evaluations now. Price main-run seed/update options after observing pilot learning speed and replacing these behavior-dependent estimates. These forecasts do not guarantee that both earlier seed options will fit.

## Network interruption and collection repair

Four original turns have no usable output. Three eventually returned `response expired`; one returned 404. The user approved four exact replacements with unchanged prompts, seeds and settings, retained **$0.005618** until billing resolves it, and permanently excluded original outputs. [Approval and signatures](research/learnability_probe_incident.json) preserve that record. All four replacement signatures match. The older five Phase 2 orphans still hold $0.007195.

{times}

The elapsed times are local UTC dispatch-to-observation ages, not server retention times. Server completion and deletion timestamps are not exposed. The two acknowledged futures were polled within two seconds, then encountered repeated network failures over a long wall-clock interval. The receipt-less accepted request was not collected until the runner restart. No evidence says the model was generating during those hours. Reconnection and collection were not coordinated across all pending requests.

The probe runner now pauses producers on a connection error, drains active HTTP operations, recreates the client automatically and collects every recoverable saved future concurrently before any new sampling. Startup recovery even precedes capability checks. One unavailable future cannot prevent collection of the others. A 408 still means pending and re-polls the same request ID with its hold retained. Every submission saves its deterministic request ID before dispatch and verifies the receipt. New journals record collection-start and response-received times. Heartbeat shutdown waits for active work through a stop event. It does not cancel HTTP requests. Expired payloads remain unrecoverable; originals stay held and excluded. Recovery behavior is exercised with mocked SDK requests; the replacement run had no further network interruption.

## Spend and gate

Project usage is **${probe["cost"]["project"]["spent_usd"]}**, held costs are **${probe["cost"]["project"]["held_usd"]}**, and **${probe["cost"]["project"]["available_usd"]} remains** under $50. Token-usage costs are gross estimates from observed response counts and the verified published rates; final invoices are pending. The proposed warm start and pilot fit the remaining budget under both forecast columns, but neither is authorized. Stop here for the user's decision.

Reproduce the offline work with `scripts/diagnose_phase2.py`, `scripts/measure_random_learnability.py`, `scripts/price_format_warmstart.py`, `scripts/summarize_learnability_probe.py`, `scripts/analyze_probe_recovery.py`, `scripts/reprice_learnability.py`, and `scripts/write_learnability_report.py`, using `.venv/bin/python`. The runner resumes saved probe games with zero service calls once all 32 are present. [Phase 2 diagnosis](DIAGNOSIS.md) contains the per-cell turn, error, termination and cost tables, plus three full transcripts. [Validation](results/learnability_probe/validation.json) and [offline reproduction](results/learnability_probe/reproduction.json) record the checks.
"""
    (ROOT / "LEARNABILITY.md").write_text(results)


if __name__ == "__main__":
    main()
