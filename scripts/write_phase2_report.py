"""Write the gate tables from completed measurements and verified spending."""

from decimal import Decimal
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT
from twenty_bits.budget import Ledger


def value(row, key, scale=1):
    x = row[key]
    return "—" if x is None else rounded(x, scale)


def rounded(x, scale=1):
    display = x * scale
    return f"{0.0 if abs(display) < 0.0005 else display:.3f}"


def interval(row, key, scale=1):
    if row[key] is None:
        return "—"
    ci = row[key + "_ci95"]
    return (
        f"{rounded(row[key], scale)} [{rounded(ci[0], scale)}, {rounded(ci[1], scale)}]"
        if ci
        else value(row, key, scale)
    )


def main():
    directory = ROOT / "results/phase2"
    summary = json.loads((directory / "summary.json").read_text())
    proof = json.loads((directory / "verification.json").read_text())
    pilot = json.loads((ROOT / "research/pilot_after_phase2.json").read_text())
    if summary["status"] != "complete" or proof["games_replayed"] != 300:
        raise ValueError("Complete and verify Phase 2 before writing the gate report.")
    status = Ledger(ROOT / "ledger.json").status()
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    rows = summary["cells"]
    actual = Decimal(status["spent_usd"])
    held = Decimal(status["held_usd"])
    forecast = Decimal("2.95805922")
    primary = [r for r in rows if r["model"] == config["primary_model"]]
    reference = [r for r in rows if r["model"] == config["reference_model"]]
    valid_primary = sum(r["valid_questions"] for r in primary)
    attribute_primary = sum(r["valid_attribute_only_questions"] for r in primary)
    zero_primary = sum(r["zero_eig_valid_questions"] for r in primary)

    def model_name(row):
        return "Qwen3-8B" if row["model"] == config["primary_model"] else "gpt-oss-120b"

    totals = []
    for group in (primary, reference):
        totals.append(
            {
                "games": sum(r["games"] for r in group),
                "wins": sum(r["wins"] for r in group),
                "calls": sum(r["sampling_calls"] for r in group),
                "inputs": sum(r["prompt_tokens"] for r in group),
                "outputs": sum(r["output_tokens"] for r in group),
                "hits": sum(r["prompt_cache_hit_tokens"] for r in group),
                "cost": sum(Decimal(r["actual_usage_cost_usd"]) for r in group),
            }
        )
    lines = [
        "# Phase 2 gate",
        "",
        "Completed 2026-11-18. Training has not started. Work stops at this gate until the user approves the condition A pilot.",
        "",
        f"The approved evaluation completed **280 Qwen3-8B games and 20 gpt-oss-120b games**. Recorded token-usage cost is **${actual}**, versus **${forecast} forecast**, or **${forecast * Decimal('1.5')} with margin**. Another **${held} is held** for the five original orphaned submissions. Available under the $50 cap is **${status['available_usd']}**. These are gross token-usage charges at the verified rate card, rounded upward per call; invoice reconciliation remains pending.",
        "",
        "![Base policy and matched baselines](results/phase2/charts/base-v-baselines.png)",
        "",
        f"Qwen won {totals[0]['wins']}/{totals[0]['games']} games; the capped reference won {totals[1]['wins']}/{totals[1]['games']}. Of {valid_primary} valid Qwen questions, {attribute_primary} were attribute-only and {zero_primary} had zero current EIG. Every valid Qwen question used item-name enumeration; validity alone did not produce useful search. EIG includes losses and invalid questions. The chart's offline policies use the same 28 frozen cases in each cell. The reference has five cases per cell and only 512 generated tokens including analysis, so it is a limited sanity slice.",
        "",
        "## Fixed settings and validation",
        "",
        "Qwen3-8B uses thinking disabled, 2,048 output tokens, a 32K context window, temperature 0.7, top-p 1, top-k disabled, and a deterministic generation seed per game and turn. The reference uses medium reasoning with a 512-token cap. Games are indices 0 through 27 in each primary cell; reference games are indices 0 through 4 in the four N=32 cells. No 4B screen, tools/foods paid evaluation, or training was run.",
        "",
        "Before paid sampling, cookbook/native rendering matched all 280 primary prompts, all 20 reference prompts, and 259 histories including long name lists. The reference's built-in system header, medium reasoning setting, and template date were pinned to match its native template. The frozen bank and public prompt hashes remain unchanged. [Rendering proof](research/phase2_rendering.json) and [sampling configuration](evals/phase2.json) record the check.",
        "",
        f"The exact engine replayed all {proof['games_replayed']} games and {proof['turns_replayed']} turns, including every posterior and EIG update. {proof['context_limit_losses_verified']} context-limit losses were checked against the rendered context size. [Verification](results/phase2/verification.json) confirms the ledger matches all used sampling calls, no orphaned output entered a result, and no training operation occurred. All 76 tests passed in a fresh environment. The test command is `python3 -m unittest discover -s tests -v`.",
        "",
        "## Per-cell performance",
        "",
        "Brackets contain 95% percentile-bootstrap intervals from 10,000 whole-game resamples. Win percentages use the observed games, not only valid games. Questions/win is undefined without a win. All-loss or all-win bootstrap intervals collapse; supplementary Wilson win intervals in summary.json retain finite-sample uncertainty.",
        "",
        "| Model | Domain | N | p | Wins/games | Win % [CI] | EIG/question [CI] | Questions/win [CI] |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {model_name(r)} | {r['domain']} | {r['n']} | {r['noise']} | {r['wins']}/{r['games']} | {interval(r, 'win_rate', 100)} | {interval(r, 'eig_per_question')} | {interval(r, 'questions_per_win')} |"
        )
    lines += [
        "",
        "## Behavior",
        "",
        "Invalid and enumeration rates are per question. Format errors and truncation are per generated action. Legal enumeration requires a parsed predicate; the raw equality diagnostic also counts attempted item-name predicates that were invalid or truncated. Predicate length counts native tokens over counted questions, including malformed ASK expressions; an extra ASK rejected in the final-guess slot is not a question. Re-check is the next-action semantic re-ask count divided by opportunities following answers with predictive probability below 0.20. Repeating an uninformative predicate can raise this rate without helping search, so it does not establish robustness alone.",
        "",
        "| Model | Domain | N | p | Format % | Invalid % | Truncation % | Context loss % | Legal enum % | Raw equality % | Predicate tokens/Q | Re-check/opportunities |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {model_name(r)} | {r['domain']} | {r['n']} | {r['noise']} | {value(r, 'format_error_rate', 100)} | {value(r, 'invalid_rate', 100)} | {value(r, 'truncation_rate', 100)} | {value(r, 'context_overflow_rate', 100)} | {value(r, 'enumeration_rate', 100)} | {value(r, 'raw_item_equality_attempt_rate', 100)} | {value(r, 'predicate_tokens')} | {r['low_probability_reasks']}/{r['low_probability_opportunities']} |"
        )
    lines += [
        "",
        "## Tokens, caching, and cost",
        "",
        "Caching applies in the live sampling sessions. The saved response field prompt_cache_hit_tokens supplies the hit count; no cache saving was credited in the forecast. Reasoning means visible generated analysis tokens. Qwen's disabled-thinking setting does not measure internal computation. Every full turn, including invalid or truncated output, contributes to token cost.",
        "",
        "| Model | Domain | N | p | Generated tokens/game | Reasoning tokens/game | Cache hit tokens | Cache hit % | Actual USD | Forecast USD |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(
            f"| {model_name(r)} | {r['domain']} | {r['n']} | {r['noise']} | {value(r, 'output_tokens_per_game')} | {value(r, 'reasoning_tokens_per_game')} | {r['prompt_cache_hit_tokens']:,} | {value(r, 'prompt_cache_hit_fraction', 100)} | {r['actual_usage_cost_usd']} | {r['forecast_usd']} |"
        )
    lines += [
        "",
        f"Total reported cache hits: {sum(t['hits'] for t in totals):,} tokens. Total generated tokens: {sum(t['outputs'] for t in totals):,}. Forecasting 64 Qwen output tokens per turn was too optimistic for long invalid outputs; caching offsets some input cost. Actual versus forecast is reported per cell rather than hiding the output-length miss inside the project cap.",
        "",
        "## Adapter incident and recovery",
        "",
        "The manually assembled sampling request omitted the stock SDK's sampling-backpressure header. Tinker returned an outdated-SDK error despite SDK 0.39.1 being current. Adding a version header alone did not fix it. Matching the native SDK wire body and X-Tinker-Sampling-Backpressure: 1 restored acceptance. A local HTTP test now compares the production adapter with the SDK's actual request builder.",
        "",
        "Five originals have no saved receipts and remain **orphaned, possibly billed** in ledger.json and the report, with **$0.007195 held until billing resolves them**. Their output is permanently excluded, even if it becomes available later. The user approved five exact replacements. Their saved prompt-and-seed signatures match the originals. Four later explicit HTTP 422 rejections were reconciled at $0.",
        "",
        f"Every sampling request after the user's additional requirement now saves its deterministic sampler-ID/sequence request ID in the fsynced journal and ledger **before creating the HTTP task**, and checks the server receipt against it. This was verified for {proof['new_calls_with_id_saved_before_dispatch_and_matching_receipt']} calls. Eleven accepted calls from the earlier completed game were made before the write-ahead ID change. Metadata and retrieval operations also persist a ledger operation ID before I/O. A retrieve_future 408 retains the sampling hold and re-polls the same saved request ID; sampling is not resubmitted.",
        "",
        "A local restart recovered four acknowledged futures. One additional local task was interrupted before server acceptance: its saved ID returned 404 and was absent from the full completion inventory while later sequences were present. That unaccepted attempt was recorded at $0 and repeated with the same prompt and seed. Shutdown now stops new submissions and drains active HTTP tasks. [Incident record](research/phase2_incident.json), [restart evidence](research/phase2_restart_recovery.json), [usage journal](results/phase2/usage.jsonl), and [ledger reconciliation](results/phase2/ledger_reconciliation.json) preserve the details.",
        "",
        "## Pilot proposal, not authorization",
        "",
        f"The noiseless animals N=32 base used {pilot['observed_output_tokens_per_call']:.1f} generated tokens per call on average; the 95th percentile was {pilot['observed_output_tokens_per_call_p95']:.1f}. The next forecasts use that observed mean as an explicit proxy, including for unmeasured N=16. They charge full per-turn contexts for training and give caching no credit. A $0.10 storage allowance bounds four sampler snapshots of at most 64 GB each for two hours at the published storage rate. Storage and all calls still need individual reservations before use.",
        "",
        "| A-only pilot | Training games | Development games | Observed-output proxy USD | With 1.5× margin USD | Cap-output stress with margin USD |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for option in pilot["pilot_options"]:
        observed = option["estimates"]["observed_base_output_proxy"]
        stress = option["estimates"]["output_cap_stress"]
        lines.append(
            f"| {option['updates']} updates, groups of 8 | {option['training_games']} | {option['development_games']} | {observed['total_usd']:.2f} | {observed['with_margin_usd']:.2f} | {stress['with_margin_usd']:.2f} |"
        )
    lines += [
        "",
        "Recommend the 16-update A pilot as a bounded diagnostic, with eight updates at N=16 then eight at N=32. Log reward, win rate, EIG, invalid rate, and group reward variance each update; evaluate the same eight development games at updates 0, 4, 8, and 16. The reward remains +1 win, −0.03/question, and −0.1/invalid. EIG never enters the reward. If all eight returns in a group are identical, standardized advantages are zero; report that rather than claiming a learning update occurred.",
        "",
        "At that pilot gate, report learning speed and the early-guess, singleton search, large name-list, and parsing audit. Then price Option S (A: three seeds, B: two) and Option U (A: two, B: one) with the updates that fit remaining funds, training games per seed, evaluated checkpoints, and 1.5× margin. No main-run choice is made here. Legal enumeration will remain legal and will be reported as a result.",
        "",
        "## Limits and reproduction",
        "",
        "Animal rows are profiles with underlying types shared across the training and held-out pools. The worlds and structured grammar are deliberately limited. This gate measures a base policy, not an RL effect. A formatting failure and a low-information legal question have different causes but both reduce the primary EIG measure. The reference cap and small sample prevent a broad model-size claim. Noise re-check conclusions require enough eligible answers; an undefined or tiny denominator is not evidence of trust or robustness.",
        "",
        "Rebuild offline with `python3 scripts/summarize_phase2.py`, `python3 scripts/verify_phase2.py`, `python3 scripts/plot_phase2.py`, `python3 scripts/price_pilot.py`, and `python3 scripts/write_phase2_report.py`. [All cell CIs](results/phase2/summary.json), [CSV](results/phase2/summary.csv), and [complete game traces](results/phase2/games.jsonl.gz) are saved. The local runner resumes saved requests and completed games; it does not start training. .env is ignored and untracked.",
        "",
    ]
    (ROOT / "PHASE2.md").write_text("\n".join(lines))
    budget = f"""# Current budget

The user approved **$50 total Tinker spend including active holds on 2026-11-18**. The approval is recorded in ledger.json. Phase 2 recorded **${actual}** in gross token-usage charges; **${held} remains held** for five originals labeled orphaned, possibly billed. Available under the cap is **${status["available_usd"]}**. Invoice reconciliation remains pending. Original outputs are permanently excluded.

The Phase 2 forecast was ${forecast}, or ${forecast * Decimal("1.5")} with margin. Its token-capped uncached envelope was $17.647606. Every paid call reserved the larger of its estimate times 1.5 and its full declared maximum before I/O. The reservation, dispatch, settlement, and 408 rules in twenty_bits/budget.py are unchanged apart from the explicitly approved $50 cap and matching validation messages.

The current gate is [PHASE2.md](PHASE2.md). [Per-cell actual versus forecast costs](results/phase2/summary.csv), [usage evidence](results/phase2/usage.jsonl), and [reconciliation](results/phase2/ledger_reconciliation.json) are saved. Pending work keeps its hold; a retrieve_future 408 re-polls the same request ID. New sampling IDs are durable before HTTP dispatch.

The next pilot is condition A with groups of eight and still needs approval. [Measured pilot forecasts](research/pilot_after_phase2.json) include output-length sensitivity, 1.5× margin, and checkpoint storage. Option S and Option U will be priced after measuring pilot learning speed. No training or main schedule is active.

[PAID_PLANS.md](PAID_PLANS.md) records the approval and preserves the superseded Phase 1 proposals. The earlier 32-update, five-seed schedule no longer fits after doubling group size. Historical cost_projection.json and twenty_bits/costs.py use the earlier 40-cell grid and are not current plans.
"""
    (ROOT / "BUDGET.md").write_text(budget)
    print({"report": "PHASE2.md", "spent_usd": str(actual), "held_usd": str(held)})


if __name__ == "__main__":
    main()
