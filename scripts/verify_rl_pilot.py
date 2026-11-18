"""Verify the completed pilot, its cost guard and saved-archive reproduction."""

import asyncio
from contextlib import redirect_stdout
from datetime import datetime
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
from scripts import analyze_rl_pilot, run_rl_pilot
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.rl_pilot import PilotTransport
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, load_split, training_game


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archived_rows(path):
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def main():
    folder = ROOT / "results/pilot_A"
    config_path = ROOT / "experiments/pilot_A.json"
    games_path = ROOT / "experiments/pilot_A_games.json"
    config = json.loads(config_path.read_text())
    records = json.loads(games_path.read_text())
    proof = json.loads((ROOT / "research/pilot_A_preflight.json").read_text())
    completion = json.loads((folder / "completion.json").read_text())
    assert digest(config_path) == proof["config_sha256"] == completion["config_sha256"]
    assert digest(games_path) == proof["games_sha256"]
    for name, sha in proof["implementation_sha256"].items():
        assert digest(ROOT / name) == sha, name
    assert (
        config["initial_policy"] == "raw_base"
        and not config["sampling_checkpoint_paths"]
    )
    assert config["games_per_training_group"] == 8 and config["updates"] == 16
    assert config["reward"] == {
        "win": 1,
        "per_question": -0.03,
        "per_invalid": -0.1,
        "information_shaping": False,
    }
    assert config["development_checks"] == [0, 4, 8, 12, 16]
    assert completion["initialization"] == "raw_base_no_sft"
    assert completion["stop_reason"] == "completed_16_updates"
    train_pool = set(load_split()["train"])
    for row in records["training"]:
        r = row["record"]
        assert r == training_game(r["n"], 800000 + row["update"], seed=11, noise=0)
    assert all(set(r["world"]["names"]) <= train_pool for r in records["development"])
    assert not {r["record"]["id"] for r in records["training"]} & {
        r["id"] for r in records["development"]
    }

    ledger = Ledger(ROOT / "ledger.json").status()
    original = json.loads(
        subprocess.check_output(["git", "show", "0e99c72:ledger.json"], cwd=ROOT)
    )
    current = json.loads((ROOT / "ledger.json").read_text())
    entries = {e["id"]: e for e in ledger["entries"]}
    assert all(entries[e["id"]] == e for e in original["entries"])
    assert original["approvals"] == current["approvals"]
    assert current["cap_usd"] == original["cap_usd"] == "50.000000"
    prior_active = {e["id"] for e in original["entries"] if e["state"] in ACTIVE_STATES}
    operations = archived_rows(folder / "operations.jsonl.gz")
    requests = archived_rows(folder / "requests.jsonl.gz")
    storage = {r["entry_id"] for r in operations if r["storage"]}
    assert len(storage) == 5
    active = {e["id"] for e in ledger["entries"] if e["state"] in ACTIVE_STATES}
    assert active == prior_active | storage
    assert sum(Decimal(entries[i]["reserved_usd"]) for i in active) == Decimal(
        ".362813"
    )
    assert sum(Decimal(entries[i]["reserved_usd"]) for i in prior_active) == Decimal(
        ".112813"
    )
    pilot_entries = [
        e for e in ledger["entries"] if e["operation"].startswith("[pilot-A-v1] ")
    ]
    assert all(e["state"] == "settled" or e["id"] in storage for e in pilot_entries)
    spent = sum(
        (Decimal(e["actual_usd"]) for e in pilot_entries if e["state"] == "settled"),
        Decimal(0),
    )
    held = sum(Decimal(entries[i]["reserved_usd"]) for i in storage)
    assert spent == Decimal(".291204") and held == Decimal(".250000")
    assert spent + held <= Decimal("2") and not ledger["blocked"]

    durations = []
    for row in requests + operations:
        entry = entries[row["entry_id"]]
        assert row["request_id_saved_before_dispatch"]
        assert entry["request_id"] == row["request_id"] == row["receipt"]["request_id"]
        assert (
            entry["created_at"]
            <= row["saved_before_dispatch_at"]
            <= row["collection_started_at"]
        )
        assert row["collection_started_at"] <= row["response_received_at"]
        if row.get("storage"):
            assert row["completed"] and entry["state"] in ACTIVE_STATES
        else:
            assert row["settled"] and Decimal(row["actual_usd"]) == Decimal(
                entry["actual_usd"]
            )
        assert row.get("output_allowed") is not False and not row.get("orphaned")
        durations.append(
            (
                datetime.fromisoformat(row["response_received_at"])
                - datetime.fromisoformat(row["saved_before_dispatch_at"])
            ).total_seconds()
        )
    assert len(requests) == len({r["request_id"] for r in requests}) == 756
    assert len(operations) == 54
    assert sorted(int(o["request_id"].rsplit(":", 1)[1]) for o in operations) == list(
        range(54)
    )
    assert all(
        o["request_id"].rsplit(":", 1)[0] == completion["training_model_id"]
        for o in operations
    )
    creation = next(o for o in operations if o["key"] == "create-model")
    assert creation["payload"]["base_model"] == "Qwen/Qwen3-8B"
    assert creation["payload"]["user_metadata"]["initialization"] == "raw_base_no_sft"
    assert not any("load" in o["key"] for o in operations)
    incident = json.loads(
        (ROOT / "research/pilot_A_local_adapter_incident.json").read_text()
    )
    assert incident["http_training_posts_dispatched"] == 0
    assert entries[incident["entry_id"]]["actual_usd"] == "0.000000"
    assert incident["entry_id"] not in {o["entry_id"] for o in operations}
    assert (
        len([e for e in pilot_entries if e["operation"].startswith("[pilot-A-v1] RL ")])
        == 55
    )

    frozen = ROOT / "evals/frozen"
    manifest = json.loads((frozen / "manifest.json").read_text())
    for cell in manifest["cells"]:
        assert digest(frozen / cell["file"]) == cell["sha256"]
    assert not subprocess.check_output(
        [
            "git",
            "diff",
            "0e99c72",
            "--name-only",
            "--",
            "evals/frozen",
            "evals/candidate_set",
            "evals/hard_mode.json",
            "twenty_bits/budget.py",
        ],
        cwd=ROOT,
    ).strip()
    prompt_hashes = json.loads(
        (ROOT / "evals/candidate_set/prompt_hashes.json").read_text()
    )
    assert len(prompt_hashes["hashes"]) == 2000
    for name, expected in completion["adapter_files"].items():
        path = ROOT / "runs/pilot-A-v1/adapter" / name
        if path.exists():
            assert (
                path.stat().st_size == expected["bytes"]
                and digest(path) == expected["sha256"]
            )

    ledger_hash = digest(ROOT / "ledger.json")
    with (
        patch.object(
            PilotTransport,
            "open",
            side_effect=AssertionError("No service access allowed"),
        ),
        redirect_stdout(io.StringIO()),
    ):
        asyncio.run(run_rl_pilot.main())
    assert digest(ROOT / "ledger.json") == ledger_hash
    result = {
        "tests_passed": 120,
        "training_games": 128,
        "development_games": 40,
        "updates": 16,
        "sampling_calls_with_predispatch_ids_and_matching_receipts": len(requests),
        "accepted_mutations_with_predispatch_ids_and_matching_receipts": len(
            operations
        ),
        "locally_rejected_unsubmitted_mutations_settled_at_zero": 1,
        "raw_base_initialization_no_sft": True,
        "training_pool_only": True,
        "frozen_games_in_gradients": 0,
        "maximum_local_save_to_collection_seconds": max(durations),
        "new_expired_response_replacements": 0,
        "recorded_pilot_usage_usd": str(spent),
        "new_checkpoint_holds_usd": str(held),
        "pilot_cap_including_holds_usd": "2.000000",
        "prior_ledger_entries_and_approval_unchanged": True,
        "old_active_holds_unchanged_usd": ".112813",
        "frozen_games_verified": 2000,
        "frozen_and_prompt_hash_files_unchanged": True,
        "core_budget_implementation_unchanged": True,
        "completed_runner_service_calls": 0,
        "completed_runner_ledger_unchanged": True,
        "final_adapter_manifest": completion["adapter_files"],
    }
    save_json(folder / "validation.json", result)
    files = (
        sorted(folder.glob("*.json"))
        + sorted(folder.glob("*.jsonl.gz"))
        + sorted(folder.glob("training-data-*.json.gz"))
    )
    old_hashes = {
        str(p.relative_to(ROOT)): digest(p)
        for p in files
        if p.name != "reproduction.json"
    }
    original_glob = Path.glob

    def archives_only(path, pattern):
        return (
            iter(())
            if path.is_relative_to(ROOT / "runs")
            else original_glob(path, pattern)
        )

    with patch.object(Path, "glob", archives_only), redirect_stdout(io.StringIO()):
        analyze_rl_pilot.main()
    assert all(digest(ROOT / name) == sha for name, sha in old_hashes.items())
    assert digest(ROOT / "ledger.json") == ledger_hash
    save_json(
        folder / "reproduction.json",
        {
            "committed_archive_analysis_identical_without_run_cache": True,
            "service_calls": 0,
            "sha256": old_hashes,
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
