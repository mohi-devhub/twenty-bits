"""Write the final main-seed gate from verified archives and factual notes."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.write_main_seed_gate import num, percent, interval, bins
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def read(name):
    return json.loads((ROOT / name).read_text())


def paragraphs(values):
    return [line for value in values for line in [value, ""]]


def main():
    summary = read("results/main_B41/summary.json")
    comparison = read("results/main_B41/all_seeds.json")
    validation = read("results/main_B41/validation.json")
    complete = read("results/main_B41/completion.json")
    proof = read("research/main_B41_preflight.json")
    assessment = read("research/main_B41_assessment.json")
    migration = read("research/ledger_migration.json")
    performance = read("research/ledger_performance_after_migration.json")
    budget = Ledger.snapshot_status(ROOT / "ledger.json")
    lines = [
        "# Main B seed 41 gate",
        "",
        "Completed the declared 30 updates and 240 noisy training games, 64 development games and immediate 280-game frozen endpoint. Raw frozen control (280 games) and raw development control (eight games) are reused unchanged. Both native endpoint file types have no expiry. **All three approved main seeds are complete; stop here before any further paid work.**",
        "",
        *paragraphs(assessment["learning_assessment"]),
        "![All scheduled endpoints](results/main_B41/charts/all-endpoints.png)",
        "",
        "## Fixed setup",
        "",
        "Fresh provider Qwen3-8B, no project SFT or pilot adapter; rank-32 LoRA seed 41; training answers flip independently across question positions within each game with p=0.10. The eight members of a group share its table, target and seeded question-index flip schedule; action-generation seeds differ. One eight-game group per update, unchanged group-standardized outcome-only returns and importance-sampling objective. Reward is +1 win, -0.03/question and -0.1/INVALID. EIG is measured, never rewarded. Thinking is disabled; output cap 2,048, context cap 32K, temperature 0.7, top-p 1 and top-k disabled. Prompts, grammar, aliases, question caps and frozen cases stayed unchanged.",
        "",
        "| N | Updates | Training games |",
        "| ---: | --- | ---: |",
    ]
    for r in proof["curriculum"]:
        lines.append(
            f"| {r['n']} | {r['update_start']}–{r['update_end']} | {8 * (r['update_end'] - r['update_start'] + 1)} |"
        )
    lines += [
        "",
        "N=32 and N=128 match the frozen animal cells. All gradients use animals from the fixed 200-row training pool; development, held-out rows and synthetic tables never enter gradients. B changes training noise to p=0.10; the same eight noiseless N=4/8 development cases remain a small common check. Only the scheduled endpoint is retained. No model, seed or checkpoint was selected on frozen scores.",
        "",
        "## Every training update",
        "",
        "Groups are sampled before the corresponding optimizer step. Changing targets and N confound raw training slopes; the fixed development curve measures matched behavior. Nonconstant returns can reflect question/invalid costs without any wins.",
        "",
        "| Update | N | Reward | Wins/8 | EIG/Q | Q/win | Legal enum % | Invalid % | Nonconstant / cumulative % | Output tokens/game |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for r in summary["updates"]:
        lines.append(
            f"| {r['update']} | {r['n']} | {num(r['mean_reward'])} | {r['wins']}/8 | {num(r['eig_per_question'])} | {num(r['questions_per_win'], 2)} | {percent(r['enumeration_rate'])} | {percent(r['invalid_question_rate'])} | {percent(r['nonzero_group_fraction'])} / {percent(r['cumulative_nonzero_group_fraction'])} | {num(r['output_tokens_per_game'], 2)} |"
        )
    signal = summary["group_signal_audit"]
    lines += [
        "",
        f"Nonconstant-return groups: {signal['nonconstant_return_groups']}/30; win variance: {signal['groups_with_win_variance']}/30. Zero-win groups: {signal['zero_win_groups']}; cost-only variance among zero-win groups: {signal['zero_win_groups_with_cost_only_variance']}. The pilot-only variance stop was not added to main training.",
        "",
        "![B41 learning curve](results/main_B41/charts/main-learning.png)",
        "",
        "## Fixed development checks",
        "",
        "| Update | Reward | Wins/8 | EIG/Q [95% CI] | Q/win | Output tokens/game |",
        "| ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for step, d in summary["development"].items():
        r = d["point"]
        lines.append(
            f"| {step} | {num(r['mean_reward'])} | {r['wins']}/8 | {interval(r['eig_per_question'], d['ci95']['eig_per_question_ci95'])} | {num(r['questions_per_win'], 2)} | {num(r['output_tokens_per_game'], 2)} |"
        )
    lines += [
        "",
        "These eight cases never enter gradients. Their intervals resample games and do not measure B training-seed variability.",
        "",
        "![All development checks](results/main_B41/charts/all-development.png)",
        "",
        "## All three seeds on every frozen cell",
        "",
        "Every policy uses the same 28 frozen cases per cell and requested evaluation seeds. EIG is question-weighted within a cell, including losses and INVALID. Ambiguous and no-guess percentages use all games, not only guesses. Noiseless ambiguous means k>1 in exact support; noisy ambiguous uses the fixed threshold-plus-MAP display. Full positive support stays in the archives.",
        "",
        "Early W/G counts correct guesses / attempts with fewer than ceil(log2(N)) questions. Lucky sub-floor guesses do not break the 1-bit expected-information ceiling (0.531004 at p=0.10). Win intervals are supplementary Wilson intervals; EIG intervals are 10,000 whole-game bootstrap intervals.",
        "",
        "| Domain | N | p | Policy | Wins/28 [Wilson CI] | EIG/Q [95% CI] | Q/win [95% CI] | Ambiguous guesses / 28 (%) | No guess / 28 (%) | Early W/G |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in comparison["cells"]:
        lines.append(
            f"| {r['domain']} | {r['n']} | {r['noise']:g} | {r['policy']} | {r['wins']}/28 [{percent(r['win_wilson_ci95'][0])}%, {percent(r['win_wilson_ci95'][1])}%] | {interval(r['eig_per_question'], r['ci95']['eig_per_question']['ci95'])} | {interval(r['questions_per_win'], r['ci95']['questions_per_win']['ci95'])} | {r['ambiguous_guesses']} ({percent(r['ambiguous_guess_rate'])}%) | {r['no_guess_games']} ({percent(r['no_guess_rate'])}%) | {r['early_guess_wins']}/{r['early_guesses']} |"
        )
    lines += [
        "",
        "### Dominant failure mode by seed",
        "",
        *paragraphs(assessment["dominant_failure_modes"]),
        "![Noiseless stopping behavior](results/main_B41/charts/all-stopping.png)",
        "",
        "### Paired B41 versus raw base",
        "",
        "| Declared noiseless subset | Metric | Raw | B41 | Paired change [95% CI] |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for label, measurements in summary["frozen_evaluation"]["declared_subsets"].items():
        for key, r in measurements.items():
            lines.append(
                f"| {label} | {key} | {num(r['base'])} | {num(r['endpoint'])} | {interval(r['final_minus_base'], r['ci95'])} |"
            )
    lines += [
        "",
        "### B41 versus the mean A endpoint",
        "",
        "The following changes give equal weight to cells and the two A seeds. Bootstrap draws resample A seeds, then paired complete games with shared draws between noise variants. **B has only one training seed**, so these intervals condition on B41 and cannot estimate B training-seed variability. Undefined re-check ratios stay undefined; differing opportunity counts can change their interpretation.",
        "",
        "| Subset | Metric | B41 minus mean A [95% CI] | Defined draws/10,000 |",
        "| --- | --- | --- | ---: |",
    ]
    for label, measurements in comparison["B41_vs_mean_A"]["subsets"].items():
        for key, r in measurements.items():
            lines.append(
                f"| {label} | {key} | {interval(r['B41_minus_mean_A'], r['ci95'])} | {r['defined_draws']} |"
            )
    lines += [
        "",
        "All conditional per-seed paired changes and unadjusted paired tests remain in [all_seeds.json](results/main_B41/all_seeds.json). With two A seeds and one B seed, inference about training conditions remains limited.",
        "",
        "## Guess with k remaining",
        "",
        "Entries are wins/guesses; all eight games remain in each row's denominator. Noisy display singleton does not imply full posterior certainty.",
        "",
        "| Development update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess/8 |",
        "| ---: | --- | --- | --- | --- | ---: |",
    ]
    for step, d in summary["development"].items():
        g = d["point"]["guess_with_k_remaining"]
        lines.append(
            f"| {step} | " + " | ".join(bins(g)) + f" | {g['no_guess_games']} |"
        )
    lines += [
        "",
        "| Training update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess/8 |",
        "| ---: | --- | --- | --- | --- | ---: |",
    ]
    for r in summary["updates"]:
        g = r["guess_with_k_remaining"]
        lines.append(
            f"| {r['update']} | " + " | ".join(bins(g)) + f" | {g['no_guess_games']} |"
        )
    lines += [
        "",
        "## Noisy re-checking and behavior",
        "",
        "| Noisy cell | Policy | Re-asks / opportunities |",
        "| --- | --- | --- |",
    ]
    for r in comparison["cells"]:
        if r["noise"] == 0.1:
            lines.append(
                f"| {r['domain']} N={r['n']} | {r['policy']} | {r['low_probability_reasks']}/{r['low_probability_opportunities']} |"
            )
    references = read("results/phase2/matched_baselines.json")
    for row in references:
        if row["policy"] == "greedy_predicate" and row["noise"] == 0.1:
            opportunities = row["low_probability_opportunities"]
            repeats = (
                round(opportunities * row["reask_after_low_probability_rate"])
                if opportunities
                else 0
            )
            lines.append(
                f"| {row['domain']} N={row['n']} | Greedy Bayesian reference | {repeats}/{opportunities} |"
            )
    lines += [
        "",
        "An opportunity follows an answer whose predictive probability is below 0.20. A next-action truth-vector repeat or complement counts as a re-ask. This narrow measure misses other cross-checks and can be inflated by uninformative repeats.",
        "",
        "![Re-check counts and opportunities](results/main_B41/charts/all-rechecks.png)",
        "",
        *paragraphs(assessment["behavior_assessment"]),
        "| Frozen cell | B41 format % | Invalid % | Truncation % | Legal enum % | Predicate tokens/Q |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in summary["frozen_evaluation"]["cells"]:
        m = r["endpoint"]
        lines.append(
            f"| {r['domain']} N={r['n']} p={r['noise']:g} | {percent(m['format_error_rate'])} | {percent(m['invalid_rate'])} | {percent(m['truncation_rate'])} | {percent(m['enumeration_rate'])} | {num(m['predicate_tokens'], 2)} |"
        )
    lines += [
        "",
        "Format and truncation rates use generated actions; invalid and enumeration rates use counted questions. A non-GUESS after the allowed answers is a format/rule error that adds no question. [Two preselected paired development examples](results/main_B41/EXAMPLE_GAMES.md).",
        "",
        "### Invalid candidate-name references, B41",
        "",
        "This post-hoc lexical audit counts exact candidate-name references in raw ASK bodies, including malformed bare names and lists. It does not accept, repair or reward them. Legal item-equality enumeration is reported separately; no legal form was banned.",
        "",
        "| Scope | Counted Q | Invalid name references | Bare names | Raw name lists | Lists ≥ N/4 | Consecutive different bare names |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scope, audit in comparison["B41_invalid_name_reference_audit"].items():
        c = audit["counts"]
        lines.append(
            f"| {scope} | {c.get('counted_questions', 0)} | {c.get('invalid_questions_with_name_references', 0)} | {c.get('bare_candidate_name_questions', 0)} | {c.get('name_list_questions', 0)} | {c.get('lists_at_least_quarter_original_N', 0)} | {c.get('consecutive_different_bare_names', 0)} |"
        )
    lines += [
        "",
        "### Sampler versus trainer log probabilities",
        "",
        "| Seed | Update-mean gap range (nats) | Maximum absolute token gap (nats) |",
        "| --- | --- | ---: |",
    ]
    for policy in ["A11", "A23", "B41"]:
        d = read(f"results/main_{policy}/summary.json")[
            "sample_train_logprob_diagnostic"
        ]
        lines.append(
            f"| {policy} | {d['mean_difference_range_nats']} | {num(d['maximum_absolute_token_difference_nats'], 6)} |"
        )
    lines += [
        "",
        "Native token sequences match; the backend cause of the gaps is unestablished. The declared importance-sampling loss uses recorded rollout log probabilities. No correction or experiment setting changed.",
        "",
        "## Offline budget-visibility check",
        "",
        "Every one of A23's 110 post-budget ASK inputs included the fixed maximum and final-guess rule in history. None included a per-turn remaining count or an explicit exhaustion notice. Usage had to be counted from the played action history. At N=128 the opening settings are exactly:",
        "",
        "```text",
        "Answer flip probability: 0.00, independently each question. Maximum questions: 14. After the last answer, make one final guess; another question loses. Begin.",
        "```",
        "",
        "Later environment messages contain YES/NO/INVALID and candidate feedback only. All 110 native token sequences matched their archived rollout inputs. B41 uses the same rendering, with the declared noise field appropriate to each game. Nothing was added to the prompt. [Exact audit](research/BUDGET_VISIBILITY.md), [all cases](research/A23_budget_visibility.json).",
        "",
        "## Ledger migration and execution",
        "",
        f"Before B41, all {migration['entries']:,} records and every approval/block were migrated without changing usage (${migration['before']['spent_usd']}) or holds (${migration['before']['held_usd']}). The live SQLite ledger uses durable small transactions, indexed entries, integer microdollar totals and append-only change records. Sampling/training/metadata still pass through Ledger.call. Reservation multiplier, cap, unknown-cost holds, 408 behavior, request IDs and settlement rules are unchanged. ledger.json is an explicit offline audit export; it is not rewritten during collection.",
        "",
        f"The original budget contracts, migration failures and mocked SQLite SDK workflows passed 216 tests before sampling. Five alternating disposable-copy trials measured median {performance['median_seconds']['json']:.3f} s for JSON versus {performance['median_seconds']['sqlite'] * 1000:.3f} ms for SQLite. A 16-player simulation had zero errors and {performance['event_loop_probe']['maximum_event_loop_lag_seconds'] * 1000:.1f} ms maximum event-loop lag. Execution therefore returned to 16 games; the 45-second HTTP timeout and scientific caps stayed fixed. These are local bookkeeping measurements, not model/network throughput. [Storage and evidence](LEDGER.md).",
        "",
        "## Native endpoints and cost",
        "",
        "Both files were listed through the guarded API with nonzero sizes and expires_at=null. Pixel Miser files were untouched; no external upload was needed. The earlier two smoke files remain deleted, with their storage holds retained.",
        "",
    ]
    for kind, row in complete["checkpoints"]["30"].items():
        lines.append(
            f"- {kind}: `{row['tinker_path']}`; {row['size_bytes']:,} bytes; API expires_at=`{json.dumps(row['expires_at'])}`; paid-plan monthly estimate ${row['monthly_paid_plan_usd']}."
        )
    c = summary["cost"]
    lines += [
        "",
        f"B41 recorded usage **${c['main_B41_spent_usd']}**, retained holds **${c['main_B41_held_usd']}**, versus forecast **$9.089482 before margin / $13.634222 with 1.5x margin**. Training sampling cost ${c['sampling_by_kind_usd']['train']}, development ${c['sampling_by_kind_usd']['dev']}, endpoint ${c['sampling_by_kind_usd']['eval_endpoint']}, forward/backward ${c['gradient_usd']}. Matched raw controls add no new charge.",
        "",
        f"Project recorded usage **${budget['spent_usd']}**, held **${budget['held_usd']}**, available **${budget['available_usd']}** under the unchanged $50 cap. Usage is metered at pinned rates, pending invoice reconciliation. All older lost-original and storage holds remain. Native no-expiry reserves cover 30 days with twice measured smoke sizes and the usual 1.5x margin; future months still require reconciliation within the cap.",
        "",
        "| Newly sampled scope | Calls | Prompt tokens | Cache-hit tokens | Generated tokens |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for kind, r in c["token_usage_by_kind"].items():
        lines.append(
            f"| {kind} | {r['sampling_calls']:,} | {r['prompt_tokens']:,} | {r['prompt_cache_hit_tokens']:,} | {r['output_tokens']:,} |"
        )
    lines += [
        "",
        "### Lost requests and collection",
        "",
        "Every accepted sampling and training request ID was saved before HTTP dispatch and checked against its receipt. A 408 kept the same ID and hold. Network interruptions drain and recover saved futures before new work. Any eligible loss gets one exact replacement, with original output exclusion and its hold retained. Every new case is listed below.",
        "",
        "| Logical request | Lost original ID | Replacement ID | Original hold USD |",
        "| --- | --- | --- | ---: |",
    ]
    for r in validation["replacement_cases"]:
        lines.append(
            f"| {r['logical_key']} | `{r['original_request_id']}` | `{r['replacement_request_id']}` | {r['original_hold_usd']} |"
        )
    if not validation["replacement_cases"]:
        lines.append("| None | — | — | 0.000000 |")
    lines += [
        "",
        f"Validation passed {validation['tests_passed']} tests and checked {validation['sampling_requests_verified']:,} sampling receipts, 93 mutations, 30 reconstructed gradient batches, every frozen hash and all prior ledger entries/holds. All HTTP work is drained. Completed runners return without service access. [Validation](results/main_B41/validation.json), [archive-only reproduction](results/main_B41/reproduction.json).",
        "",
        "## Limits and next step",
        "",
        *paragraphs(assessment["limitations_and_next"]),
        "Reproduce offline using scripts/analyze_main_B41.py, scripts/analyze_all_main_seeds.py, scripts/verify_main_B41.py, scripts/plot_main_B41.py, scripts/plot_all_main_seeds.py and scripts/write_main_B41_gate.py. These read committed archives and the completed JSON audit export, without credentials or the live database.",
        "",
        "**Stopped at the B41 gate. No further Tinker work is authorized.**",
        "",
    ]
    (ROOT / "MAIN_B41_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
