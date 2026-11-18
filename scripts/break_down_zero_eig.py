"""Classify the 303 Phase 2 zero-EIG cases without changing their old grammar."""

from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.evaluation import frozen_games
from twenty_bits.predicates import parse
from twenty_bits.worlds import ROOT, World


def node_kinds(expression):
    kinds, stack = set(), [expression]
    while stack:
        node = stack.pop()
        kinds.add(node.kind)
        stack.extend(node.children)
    return kinds


def main():
    diagnosis = json.loads((ROOT / "results/diagnosis/phase2.json").read_text())
    selected = {
        (row["game_id"], row["turn_index"])
        for row in diagnosis["zero_eig_questions"]
        if row["requested_category"] == "other"
    }
    assert len(selected) == 303
    records = {}
    games = [
        json.loads(line)
        for line in gzip.open(ROOT / "results/phase2/games.jsonl.gz", "rt")
    ]
    for domain, n, noise in sorted(
        {
            (g["domain"], g["n"], g["noise"])
            for g in games
            if g["model"] == "Qwen/Qwen3-8B"
        }
    ):
        records.update({r["id"]: r for r in frozen_games(domain, n, noise, 28)})
    rows = []
    for game in games:
        if game["model"] != "Qwen/Qwen3-8B":
            continue
        world = World.from_dict(records[game["game_id"]]["world"])
        previous = []
        for index, turn in enumerate(game["turns"]):
            if not turn["is_question"] or turn["invalid"]:
                continue
            expression = parse(turn["action"][5:].strip())
            mask = expression.evaluate(world.attributes, world.names, world.rows)
            repeat = any(
                np.array_equal(mask, old) or np.array_equal(mask, ~old)
                for old in previous
            )
            assert repeat == turn["reask"]
            previous.append(mask)
            if (game["game_id"], index) not in selected:
                continue
            posterior = np.asarray(turn["posterior_before"])
            support = posterior > 0
            if mask.all():
                cause = "true_for_entire_table"
            elif not mask.any():
                cause = "false_for_entire_table"
            elif mask[support].all():
                cause = "true_for_every_remaining_candidate_only"
            elif not mask[support].any():
                cause = "false_for_every_remaining_candidate_only"
            else:
                cause = "nonconstant_but_nearly_certain_bayesian_mass"
            kinds = node_kinds(expression)
            if expression.kind == "item":
                structure = "single_item_equality"
            elif kinds <= {"item", "or"}:
                structure = "positive_item_name_or_list"
            elif kinds <= {"item", "and"}:
                structure = "positive_item_name_and_list"
            elif "attribute" not in kinds:
                structure = "other_item_boolean_predicate"
            else:
                structure = "mixed_attribute_and_item_predicate"
            rows.append(
                {
                    "game_id": game["game_id"],
                    "domain": game["domain"],
                    "n": game["n"],
                    "noise": game["noise"],
                    "turn_index": index,
                    "cause": cause,
                    "structure": structure,
                    "repeated_mask_or_complement": repeat,
                    "posterior_support": int(support.sum()),
                    "table_yes_count": int(mask.sum()),
                    "remaining_yes_count": int(mask[support].sum()),
                    "posterior_yes_mass": float(mask @ posterior),
                    "named_items": expression.named_items,
                    "eig": turn["eig"],
                    "single_item_equality_on_remaining_candidate": bool(
                        expression.kind == "item" and mask[support].any()
                    ),
                }
            )
    assert len(rows) == 303
    cross = defaultdict(Counter)
    cells = defaultdict(Counter)
    for row in rows:
        cross[row["cause"]][
            "repeated" if row["repeated_mask_or_complement"] else "not_repeated"
        ] += 1
        cells[(row["domain"], row["n"], row["noise"])][row["cause"]] += 1
    result = {
        "service_calls": 0,
        "grammar_version": "names-v1",
        "questions": 303,
        "logical_causes": dict(Counter(r["cause"] for r in rows)),
        "structures": dict(Counter(r["structure"] for r in rows)),
        "repeated_questions": sum(r["repeated_mask_or_complement"] for r in rows),
        "single_item_equality_on_remaining_candidate": sum(
            r["single_item_equality_on_remaining_candidate"] for r in rows
        ),
        "logical_cause_by_repetition": dict(cross),
        "cells": [
            {"domain": k[0], "n": k[1], "noise": k[2], "counts": dict(v)}
            for k, v in sorted(cells.items())
        ],
        "definition": "Logical causes partition the 303 questions. Repetition and expression structure are separate, overlapping views; do not add them to logical-cause counts. Remaining means strictly positive saved posterior mass. No answer or score is recomputed under the alias grammar.",
        "rows": rows,
    }
    (ROOT / "results/diagnosis/zero_eig_other.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("rows", "cells")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
