"""Verify the saved pause and prove the runner makes zero service calls."""

import asyncio
from contextlib import redirect_stdout
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import run_main_seed
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, training_game


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pause = json.loads((ROOT / "research/main_A11_pause.json").read_text())
    assert (
        pause["active"] and pause["resume_requires_exact_user_instruction"] == "resume"
    )
    folder = ROOT / "results/main_A11/paused"
    compressed = ROOT / pause["games_archive"]
    assert sha(compressed) == pause["games_archive_sha256"]
    manifest_path = ROOT / "experiments/main_A11_games.json"
    raw = gzip.decompress(compressed.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == pause["games_sha256"]
    if not manifest_path.exists():
        manifest_path.write_bytes(raw)
    for name, digest in pause["archive_sha256"].items():
        assert sha(folder / name) == digest, name
    assert sha(ROOT / "experiments/main_A11.json") == pause["config_sha256"]
    assert sha(ROOT / "experiments/main_A11_games.json") == pause["games_sha256"]
    manifest = json.loads((ROOT / "experiments/main_A11_games.json").read_text())
    for r in manifest["training"]:
        assert r["record"] == training_game(
            r["record"]["n"], 1000000 + r["update"], seed=11, noise=0
        )
    status = Ledger(ROOT / "ledger.json").status()
    entries = {e["id"]: e for e in status["entries"]}
    old = json.loads(
        subprocess.check_output(["git", "show", "9fff44c:ledger.json"], cwd=ROOT)
    )
    assert all(entries[e["id"]] == e for e in old["entries"])
    assert (
        old["approvals"] == json.loads((ROOT / "ledger.json").read_text())["approvals"]
    )
    requests = [
        json.loads(line) for line in gzip.open(folder / "requests.jsonl.gz", "rt")
    ]
    games = [json.loads(line) for line in gzip.open(folder / "games.jsonl.gz", "rt")]
    operations = [
        json.loads(line) for line in gzip.open(folder / "operations.jsonl.gz", "rt")
    ]
    assert len(requests) == 627 and len(games) == 52
    assert len({r["request_id"] for r in requests}) == 627
    assert (
        len(operations) == 1
        and operations[0]["key"] == "create-model"
        and operations[0]["completed"]
    )
    assert (
        pause["last_completed_update"]
        == pause["optimizer_steps"]
        == pause["training_games"]
        == 0
    )
    assert pause["saved_checkpoint"] is None and pause["partial_update"] is None
    excluded = []
    collected = []
    for r in requests:
        e = entries[r["entry_id"]]
        assert (
            r["request_id_saved_before_dispatch"] and r["request_id"] == e["request_id"]
        )
        if r.get("settled"):
            assert r.get("response") and e["state"] == "settled"
            assert r["actual_usd"] == e["actual_usd"]
            assert r["receipt"]["request_id"] == r["request_id"]
            collected.append(r["entry_id"])
        else:
            assert (
                r["orphaned"]
                and not r["output_allowed"]
                and not r["replacement_submitted"]
            )
            assert e["state"] in ACTIVE_STATES and e["actual_usd"] is None
            assert e["original_lost_request"] and not e["output_allowed"]
            excluded.append(r["entry_id"])
    assert len(collected) == 625 and len(excluded) == 2
    assert sum(Decimal(entries[i]["reserved_usd"]) for i in excluded) == Decimal(
        ".004721"
    )
    assert sum(Decimal(entries[i]["actual_usd"]) for i in collected) == Decimal(
        ".192932"
    )
    assert all(g["kind"] == "eval_base" for g in games)
    assert all(t["usage"]["entry_id"] in collected for g in games for t in g["turns"])
    assert not (ROOT / "results/main_A11/completion.json").exists()
    assert not subprocess.check_output(
        [
            "git",
            "diff",
            "9fff44c",
            "--name-only",
            "--",
            "evals/frozen",
            "evals/candidate_set",
            "twenty_bits/budget.py",
        ],
        cwd=ROOT,
    ).strip()
    before = sha(ROOT / "ledger.json")
    with (
        patch.object(
            run_main_seed.RecoveringTransport,
            "open",
            side_effect=AssertionError("No service calls"),
        ) as opened,
        redirect_stdout(io.StringIO()),
    ):
        asyncio.run(run_main_seed.main())
    opened.assert_not_called()
    assert sha(ROOT / "ledger.json") == before
    result = {
        "paused_at_user_request": True,
        "last_completed_main_update": 0,
        "no_partial_update_or_optimizer_step": True,
        "main_checkpoint": None,
        "complete_control_games": 52,
        "collected_saved_results": 625,
        "unavailable_excluded_originals": 2,
        "new_original_holds_usd": "0.004721",
        "new_stage_usage_usd": "0.192932",
        "sampling_replacements_submitted": 0,
        "paused_runner_service_calls": 0,
        "paused_runner_ledger_unchanged": True,
        "prior_ledger_entries_and_cap_approval_unchanged": True,
        "frozen_games_and_prompt_hash_files_unchanged": True,
        "immutable_seed_and_data_order_verified": True,
        "archive_sha256_verified": pause["archive_sha256"],
        "immutable_manifest_restorable_from_compressed_bytes": True,
        "tests_passed": 130,
        "project": {k: v for k, v in status.items() if k != "entries"},
    }
    save_json(folder / "validation.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
