"""Rebuild cell metrics, uncertainty, usage, and traces without service calls."""

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import csv
import gzip
import hashlib
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from scripts.run_baselines import summarize
from twenty_bits.budget import Ledger
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.worlds import ROOT
from twenty_bits.tinker_transport import rates


def extra_metrics(games, draws=10000):
    matrix = np.array(
        [
            [
                len(g["turns"]),
                g["format_error_count"],
                g["truncation_count"],
                g["sampling_calls"],
                g["prompt_tokens"],
                g["output_tokens"],
                g["prompt_cache_hit_tokens"],
                g["reasoning_tokens"],
                g["action_tokens"],
                g["context_overflow"],
                g["questions"],
                sum(
                    t["is_question"] and bool(re.search(r"\bitem\s*==", t["action"]))
                    for t in g["turns"]
                ),
            ]
            for g in games
        ],
        dtype=float,
    )
    n = len(games)

    def values(t):
        (
            turns,
            fmt,
            trunc,
            calls,
            prompt,
            output,
            cached,
            reasoning,
            action,
            overflow,
            questions,
            attempted_enum,
        ) = t
        return [
            fmt / turns if turns else np.nan,
            trunc / calls if calls else np.nan,
            prompt / n,
            output / n,
            cached / prompt if prompt else np.nan,
            reasoning / n,
            action / n,
            overflow / n,
            attempted_enum / questions if questions else np.nan,
        ]

    estimates = values(matrix.sum(axis=0))
    rng = np.random.default_rng(4271)
    samples = np.array(
        [values(matrix[rng.integers(n, size=n)].sum(axis=0)) for _ in range(draws)]
    )
    names = [
        "format_error_rate",
        "truncation_rate",
        "prompt_tokens_per_game",
        "output_tokens_per_game",
        "prompt_cache_hit_fraction",
        "reasoning_tokens_per_game",
        "action_tokens_per_game",
        "context_overflow_rate",
        "raw_item_equality_attempt_rate",
    ]
    result = {}
    for i, name in enumerate(names):
        result[name] = float(estimates[i]) if np.isfinite(estimates[i]) else None
        valid = samples[:, i][np.isfinite(samples[:, i])]
        result[name + "_ci95"] = (
            np.quantile(valid, [0.025, 0.975]).tolist() if len(valid) else None
        )
    result.update(
        sampling_calls=int(matrix[:, 3].sum()),
        prompt_tokens=int(matrix[:, 4].sum()),
        output_tokens=int(matrix[:, 5].sum()),
        prompt_cache_hit_tokens=int(matrix[:, 6].sum()),
        actual_usage_cost_usd=str(
            sum(
                (Decimal(t["usage"]["actual_usd"]) for g in games for t in g["turns"]),
                Decimal(0),
            )
        ),
        wins=sum(g["won"] for g in games),
        low_probability_reasks=sum(g["reasks_after_low_probability"] for g in games),
        invalid_questions=sum(g["invalid_count"] for g in games),
        format_errors=sum(g["format_error_count"] for g in games),
        truncated_outputs=sum(g["truncation_count"] for g in games),
        early_guesses=sum(g["early_guess"] for g in games),
        singleton_enumeration_questions=sum(
            g["singleton_enumeration_questions"] for g in games
        ),
        large_name_list_questions=sum(g["large_name_list_questions"] for g in games),
        valid_questions=sum(g["questions"] - g["invalid_count"] for g in games),
        valid_attribute_only_questions=sum(
            t["is_question"] and not t["invalid"] and not t["enumeration"]
            for g in games
            for t in g["turns"]
        ),
        zero_eig_valid_questions=sum(
            t["is_question"] and not t["invalid"] and t["eig"] < 1e-12
            for g in games
            for t in g["turns"]
        ),
    )
    return result


def main():
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    source = ROOT / "runs" / config["run_id"] / "games"
    directory = ROOT / "results/phase2"
    directory.mkdir(parents=True, exist_ok=True)
    games = [json.loads(p.read_text()) for p in sorted(source.glob("*.json"))]
    if not games and (directory / "games.jsonl.gz").exists():
        games = [
            json.loads(line)
            for line in gzip.decompress(
                (directory / "games.jsonl.gz").read_bytes()
            ).splitlines()
        ]
    if not games:
        raise ValueError("No saved game traces are available.")
    games.sort(
        key=lambda g: (g["model"], g["domain"], g["n"], g["noise"], g["game_id"])
    )
    # A rejected extra ASK in the terminal slot is not a counted question.
    for game in games:
        game["predicate_tokens"] = sum(
            t["predicate_tokens"] or 0 for t in game["turns"] if t["is_question"]
        )
    expected = set()
    for model in [config["primary_model"], config["reference_model"]]:
        for cell in frozen_manifest()["cells"]:
            count = config["primary_games_per_cell"]
            if model == config["reference_model"]:
                if cell["n"] not in config["reference_sizes"]:
                    continue
                count = config["reference_games_per_cell"]
            for record in frozen_games(cell["domain"], cell["n"], cell["noise"], count):
                expected.add((model, record["id"]))
    observed = {(g["model"], g["game_id"]) for g in games}
    if len(observed) != len(games) or not observed <= expected:
        raise ValueError("Duplicate or out-of-slice games in Phase 2.")
    cells = defaultdict(list)
    for game in games:
        cells[(game["model"], game["domain"], game["n"], game["noise"])].append(game)
    rows = []
    measurement = json.loads((ROOT / "research/token_measurements.json").read_text())
    for (model, domain, n, noise), group in sorted(cells.items()):
        native = next(
            c
            for c in measurement["models"][model]["cells"]
            if (c["domain"], c["n"], c["noise"]) == (domain, n, noise)
        )
        turns = 2 * (n - 1).bit_length() + 1
        output = 64 if model == config["primary_model"] else 128
        inputs = (
            turns * native["initial_prompt_tokens"]["max"]
            + (output + 32) * turns * (turns - 1) // 2
        )
        rate = rates(model)
        forecast = (
            len(group)
            * (inputs * rate["prefill"] + turns * output * rate["sample"])
            / Decimal(1_000_000)
        )
        row = {
            "model": model,
            "domain": domain,
            "n": n,
            "noise": noise,
            **summarize(group, bootstrap=10000),
            **extra_metrics(group),
            "forecast_usd": str(forecast),
            "forecast_with_margin_usd": str(forecast * Decimal("1.5")),
        }
        wins = row["win_rate"]
        z = 1.96
        denominator = 1 + z * z / len(group)
        center = (wins + z * z / (2 * len(group))) / denominator
        half = (
            z
            * (wins * (1 - wins) / len(group) + z * z / (4 * len(group) ** 2)) ** 0.5
            / denominator
        )
        row["win_rate_wilson_ci95"] = [max(0, center - half), min(1, center + half)]
        rows.append(row)
    save = {
        "status": "complete" if observed == expected else "incomplete",
        "expected_games": len(expected),
        "completed_games": len(games),
        "missing_games": sorted([list(k) for k in expected - observed]),
        "bootstrap_draws": 10000,
        "bootstrap_unit": "complete games within each cell",
        "cost_basis": "Observed tokens and reported cache hits at the verified rate card, upward microdollar rounding per call; invoice reconciliation pending",
        "cells": rows,
    }
    (directory / "summary.json").write_text(
        json.dumps(save, indent=2, allow_nan=False) + "\n"
    )
    if rows:
        scalar = [
            {k: v for k, v in row.items() if not k.endswith("_ci95")} for row in rows
        ]
        with (directory / "summary.csv").open("w") as f:
            writer = csv.DictWriter(f, fieldnames=list(scalar[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(scalar)
    ordered = sorted(
        games, key=lambda g: (g["model"], g["domain"], g["n"], g["noise"], g["game_id"])
    )
    payload = "".join(
        json.dumps(g, separators=(",", ":")) + "\n" for g in ordered
    ).encode()
    (directory / "games.jsonl.gz").write_bytes(gzip.compress(payload, mtime=0))
    journals = []
    run_directory = ROOT / "runs" / config["run_id"]
    for kind in ("requests", "rejected"):
        for path in sorted((run_directory / kind).glob("*.json")):
            raw = json.loads(path.read_text())
            compact = {k: v for k, v in raw.items() if k != "response"}
            compact["journal_kind"] = kind
            if "response" in raw:
                compact["response_sha256"] = hashlib.sha256(
                    json.dumps(raw["response"], sort_keys=True).encode()
                ).hexdigest()
            journals.append(compact)
    if journals:
        encoded = "".join(
            json.dumps(row, separators=(",", ":")) + "\n"
            for row in sorted(journals, key=lambda row: row["entry_id"])
        ).encode()
        (directory / "requests.jsonl.gz").write_bytes(gzip.compress(encoded, mtime=0))
    status = Ledger(ROOT / "ledger.json").status()
    orphaned = [
        e
        for e in status["entries"]
        if e.get("incident_status") == "orphaned, possibly billed"
    ]
    recon = {
        "cap_usd": status["cap_usd"],
        "spent_usd": status["spent_usd"],
        "held_usd": status["held_usd"],
        "available_usd": status["available_usd"],
        "orphaned_entries": [
            {
                k: e[k]
                for k in (
                    "id",
                    "operation",
                    "reserved_usd",
                    "state",
                    "incident_status",
                    "output_allowed",
                )
            }
            for e in orphaned
        ],
        "usage_sha256": hashlib.sha256(
            (directory / "usage.jsonl").read_bytes()
        ).hexdigest(),
    }
    (directory / "ledger_reconciliation.json").write_text(
        json.dumps(recon, indent=2) + "\n"
    )
    lines = [
        "# Phase 2 cell measurements",
        "",
        f"Status: {save['status']}. Completed {len(games)} of {len(expected)} approved games. Bootstrap intervals resample whole games 10,000 times.",
        "",
        "Invalid is per question. Format errors and truncation are per generated turn. Enumeration is grammar-valid item equality; raw equality attempts include invalid or truncated outputs. Questions/win is undefined when there are no wins. Cache hits count reported prompt tokens.",
        "",
        "| Model | Domain | N | p | Games | Win % | EIG/Q | Q/win | Enum % | Raw equality % | Invalid % | Format % | Truncation % | Cache hit tokens | Cost USD |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:

        def f(key, scale=1):
            return "—" if row[key] is None else f"{scale * row[key]:.3f}"

        lines.append(
            f"| {row['model']} | {row['domain']} | {row['n']} | {row['noise']} | {row['games']} | {f('win_rate', 100)} | {f('eig_per_question')} | {f('questions_per_win')} | {f('enumeration_rate', 100)} | {f('raw_item_equality_attempt_rate', 100)} | {f('invalid_rate', 100)} | {f('format_error_rate', 100)} | {f('truncation_rate', 100)} | {row['prompt_cache_hit_tokens']:,} | {row['actual_usage_cost_usd']} |"
        )
    lines.extend(
        [
            "",
            "All confidence intervals, token counts, predicate lengths, and re-ask denominators are in summary.json. A constant all-loss or all-win sample has a degenerate percentile-bootstrap interval; this does not establish a zero or perfect population rate. The reference has five games per cell and a 512-token cap including reasoning.",
            "",
        ]
    )
    (directory / "CELLS.md").write_text("\n".join(lines))
    print(
        json.dumps(
            {
                "completed": len(games),
                "expected": len(expected),
                "cells": len(rows),
                "spent_usd": status["spent_usd"],
                "held_usd": status["held_usd"],
            }
        )
    )


if __name__ == "__main__":
    main()
