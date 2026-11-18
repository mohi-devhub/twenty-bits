"""Write the alias/SFT gate from completed saved results, without service calls."""

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


def pct(value):
    return f"{100 * value:.1f}%"


def main():
    alias = json.loads((ROOT / "results/alias_probe/summary.json").read_text())
    sft = json.loads((ROOT / "results/format_sft/summary.json").read_text())
    zero = json.loads((ROOT / "results/diagnosis/zero_eig_other.json").read_text())
    audit = json.loads((ROOT / "results/format_sft/behavior_audit.json").read_text())
    completion = json.loads((ROOT / "results/format_sft/completion.json").read_text())
    curve = json.loads((ROOT / "results/format_sft/learning_curve.json").read_text())[
        "updates"
    ]
    totals = sft["cost"]["project"]

    def metrics(summary):
        return table(
            [
                "N",
                "Valid turns [95% CI]",
                "Wins [Wilson 95% CI]",
                "EIG/question [95% CI]",
                "Questions/win",
            ],
            [
                [
                    c["n"],
                    f"{c['valid_turns']}/{c['turns']} = {pct(c['valid_turn_rate'])} [{', '.join(pct(x) for x in c['valid_turn_ci95_game_bootstrap'])}]",
                    f"{c['wins']}/{c['games']} [{', '.join(pct(x) for x in c['win_wilson_ci95'])}]",
                    f"{c['metrics']['eig_per_question']:.4f} [{', '.join(f'{x:.4f}' for x in c['metrics']['eig_per_question_ci95'])}]",
                    f"{c['metrics']['questions_per_win']:.2f}"
                    if c["wins"]
                    else "undefined",
                ]
                for c in summary["cells"]
            ],
        )

    def causes(summary):
        return table(
            ["N", "Remaining invalid-turn cause", "Count"],
            [
                [c["n"], cause, count]
                for c in summary["cells"]
                for cause, count in sorted(c["remaining_invalid_turn_causes"].items())
            ],
        )

    zero_table = table(
        ["Logical cause", "Questions", "Repeated split/complement"],
        [
            [name, count, zero["logical_cause_by_repetition"][name].get("repeated", 0)]
            for name, count in zero["logical_causes"].items()
        ],
    )
    means = {
        epoch: sum(
            r["action_nll"] * r["examples"] for r in curve if r["epoch"] == epoch
        )
        / sum(r["examples"] for r in curve if r["epoch"] == epoch)
        for epoch in (1, 2)
    }
    counts = audit["counts"]
    example = audit["examples"][0]
    example_text = "\n".join(
        f"{t['action']} -> {t['answer']}" for t in example["turns"]
    )
    greedy = audit["paired_greedy_reference"]
    report = f"""# Attribute aliases and qualification gate

The parser-only probe and conditional format SFT are complete. **Qualification failed on wins: 3/32, below the required 8/32.** Pooled valid turns were {pct(sft["pooled_valid_turn_rate"])}, above the 90% format requirement. No RL update ran. Stop at this gate.

## Exact grammar aliases

`attribute-codes-v2` accepts each table-header code as an exact, case-sensitive alias for its full attribute name. Full names and codes can mix, for example `ASK: a AND NOT aquatic`. The renderer and parser derive codes from the same function after constant columns are removed. There is no fuzzy matching or case folding.

An identifier in an expression denotes an attribute. A name after `item ==` denotes a literal item, so a candidate called `a` does not change the meaning of the attribute code `a`. Lowercase keyword-like codes remain distinct from uppercase operators. A bare `item` is an attribute only if the header supplies that code; `item == name` remains equality. Headers with conflicting code/full-name meanings are rejected. Tests cover these collisions, mixed identifiers, exact case, malformed/malicious inputs, and alias remapping after constant-column removal.

Historical Phase 2 and the earlier prompt probe retain `names-v1` scoring. Their saved outcomes are not rescored under changed answers. Frozen games, world files, prompt hashes, reward and question budgets are unchanged. The probe uses identical public prompt bytes, subsets, targets, output cap and requested generation seeds to the earlier 16+16 games. In particular, the prompt still requests full names; the acceptance grammar now also understands codes. This run changes the parser, not the observation or instructions. [Rendering and hash proof](research/alias_probe_rendering.json), [grammar rules](PROTOCOL.md).

## Parser-only re-probe

Qwen3-8B, thinking disabled, 2,048 output tokens, temperature 0.7, top-p 1, top-k disabled, noiseless training-pool animals. There were 16 games each at N=8 and N=16, with game seed 20261118 and the same per-turn generation seed namespace. No remaining-candidate feedback was supplied.

{metrics(alias)}

Pooled valid turns were **{alias["pooled_valid_turns"]}/{alias["pooled_turns"]} = {pct(alias["pooled_valid_turn_rate"])}**. The declared decision rule required at least 80% pooled valid turns and at least one N=8 win. It failed the format requirement and activated the user's conditional SFT approval. The probe cost **${alias["cost"]["probe_spent_usd"]}**, with no unresolved probe holds, against the **$0.25** limit including holds. Its measured prior-run forecast was $0.069563, or $0.104345 with margin. No settings changed during the run.

These are all remaining invalid-turn causes. Parser errors and final-slot failures partition the invalid turns here; truncation is a separate flag in the saved summary.

{causes(alias)}

[Probe metrics, intervals and verification](results/alias_probe/summary.json), [all games](results/alias_probe/games.jsonl.gz).

## The 303 other zero-EIG questions

All 303 were positive OR lists of item equalities. None was a singleton item equality on a remaining candidate. None was false for every remaining candidate. Their logical causes partition as follows, under the historical names-only grammar and saved posteriors.

{zero_table}

The single noisy case had nonzero probability on both answers but expected information below 1e-12 bits. Repetition is a separate behavioral dimension: **281/303** repeat an earlier truth vector or its complement. It must not be added to the logical-cause counts. The other eight questions among the original 311 named only already-eliminated items, as previously reported. Unknown item names are invalid and are not part of the 311. [Every classified question and per-cell counts](results/diagnosis/zero_eig_other.json).

## Conditional format SFT

The condition failed, so the approved warm start ran once: seed 11, rank-32 LoRA with attention, MLP and output projection trainable, AdamW learning rate 1e-4, beta1=0.9, beta2=0.95, epsilon=1e-12, no weight decay or gradient clipping. There were two passes over the frozen 554-example proposal, batches of 32, and **36 optimizer updates**. The two shuffle seeds were 11 and 12. Full-context training input totaled **827,254 tokens**.

The dataset uses fresh procedural toy tables and random single-attribute questions with replacement. Correct guesses appear only at singleton. It contains no frozen games or held-out world rows. Native/cookbook supervision prefixes matched all 554 examples. The pinned cookbook helper creates shifted inputs and targets; only the current assistant action, including its stop token, has loss weight. Prompt tokens receive zero loss weight. No EIG ranking, bisection selection, outcome reward or RL advantage enters this cross-entropy stage.

Gradient usage cost **${sft["cost"]["gradient_usd"]}**, versus $0.36399176 forecast. The difference is upward rounding across calls. Two bounded checkpoint-storage holds total **$0.100000** and remain until billing reconciliation. Both checkpoints have a two-hour TTL. The external adapter, {completion["checkpoints"]["external"]["size_bytes"]:,} bytes, is downloaded under `runs/format-warmstart-v1/adapter/` with a SHA-256 manifest, so the local copy survives hosted expiry. The native and external checkpoint URIs are recorded in [completion.json](results/format_sft/completion.json).

Mean per-example action NLL was {means[1]:.4f} nats/token in epoch 1 and {means[2]:.4f} in epoch 2. This is training fit, not game success. [All update metrics](results/format_sft/learning_curve.json).

The SFT supplies a single-attribute action prior and table-tracking examples. Later RL comparisons must use this pre-RL checkpoint as their matched control. Toy-table exposure also changes synthetic transfer into a test of new tables, labels and sizes rather than an entirely unseen random-table task.

## Qualification before RL

The separate fixed development set has 16 training-pool animal games each at N=4 and N=8, seed 20261120 and indices 600000 through 600015. These games never entered gradients. The policy sampled from the trained snapshot, not a new base sampler. The output cap, disabled-thinking setting, grammar, reward, noise and answer-only feedback stayed fixed. These are development results, not a new frozen paid evaluation or a paired estimate of the SFT effect.

{metrics(sft)}

Pooled valid turns were **{sft["pooled_valid_turns"]}/{sft["pooled_turns"]} = {pct(sft["pooled_valid_turn_rate"])}**. That passes the 90% format requirement. **3/32 wins fails the 8/32 requirement**, so qualification failed. Format validity did not establish reliable search. Confidence intervals resample complete games 10,000 times; win intervals use Wilson bounds. Undefined win-conditioned quantities remain null.

{causes(sft)}

The free consistency audit found {counts["guesses_of_eliminated_candidates"]} guesses of already-eliminated candidates, including {counts["wrong_guesses_despite_singleton"]} wrong guesses despite a singleton posterior. {counts["games_reaching_singleton"]} games reached a singleton, but only {counts["singleton_games_won"]} of those won. There were {counts["guesses_outside_candidate_table"]} guesses outside the table. Of the three wins, {counts["wins_with_singleton_posterior"]} had a singleton posterior and {counts["wins_without_singleton_posterior"]} did not. The scripted greedy-predicate policy won **{greedy["wins"]}/{greedy["games"]}** on the same qualification cases, averaging {greedy["mean_questions_per_win"]:.2f} questions and {greedy["mean_eig_per_question"]:.4f} expected bits/question. These cases are solvable under the environment rules.

One selected consistency failure, `{example["game_id"]}`, had exactly `{example["remaining_item"]}` remaining:

```text
{example_text}
```

This example illustrates a failure and is not a performance sample. [Consistency audit](results/format_sft/behavior_audit.json), [qualification metrics and CIs](results/format_sft/summary.json), [complete games](results/format_sft/games.jsonl.gz).

## Budget and next gate

SFT plus qualification recorded **${sft["cost"]["probe_spent_usd"]}** and holds **${sft["cost"]["probe_held_usd"]}**, safely inside the conservative **$2.51** combined cap including holds. Qualification sampling alone cost ${sft["cost"]["sampling_usd"]}. All operations used Ledger.call; 408 polling retains the original future and hold. Sampling IDs were durable before HTTP dispatch, and training receipts were durable before polling. No forward/backward or optimizer operation was repeated to recover a timeout.

Project usage is **${totals["spent_usd"]}**, total holds are **${totals["held_usd"]}**, and **${totals["available_usd"]} remains** under $50. The nine older excluded submissions still hold $0.012813. The additional $0.10 is checkpoint storage. Usage charges use observed response/request token counts and published rates, rounded upward per call; final invoices remain pending.

The gpt-oss-120b reference is removed from future plans. Its 20 completed games remain historical failure data because its capped reasoning consumed 157/220 turns without an action. No new reference call ran.

**No RL is approved or started.** The proposed 16-update A pilot remains N=4 for four updates, N=8 for eight, and N=16 for four, one group of eight games per update with independent member seeds and one common start state. Its required stop rule remains: after four updates, halt if fewer than 25% of groups have nonzero return variance. EIG remains measurement only. Do not lower the qualification threshold, extend SFT, change prompts, expose candidate support or start that pilot without a new decision. The next issue to resolve is guess consistency with the observed answers.

Reproduce offline with `.venv/bin/python scripts/break_down_zero_eig.py`, `scripts/summarize_alias_probe.py`, `scripts/summarize_format_sft.py`, `scripts/audit_qualification.py`, and `scripts/write_alias_gate.py`. The completed runners refuse to repeat paid work. [Validation](results/format_sft/validation.json) records unit tests, request verification and frozen-hash checks.
"""
    (ROOT / "ALIAS_GATE.md").write_text(report)


if __name__ == "__main__":
    main()
