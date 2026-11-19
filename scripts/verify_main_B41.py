"""Verify B41's durable requests, unchanged science and offline reproduction."""

import asyncio
from contextlib import redirect_stdout
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import (
    analyze_main_B41,
    analyze_all_main_seeds,
    run_main_B41,
    run_B41_stage,
)
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.rl_pilot import PilotTransport
from twenty_bits.worlds import ROOT, load_split, training_game


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in gzip.open(path, "rt")]


def main():
    out = ROOT / "results/main_B41"
    complete = json.loads((out / "completion.json").read_text())
    config = json.loads((ROOT / "experiments/main_B41.json").read_text())
    proof = json.loads((ROOT / "research/main_B41_preflight.json").read_text())
    manifest_bytes = gzip.decompress(
        (ROOT / "experiments/main_B41_games.json.gz").read_bytes()
    )
    manifest = json.loads(manifest_bytes)
    assert (
        sha(ROOT / "experiments/main_B41.json")
        == proof["config_sha256"]
        == complete["config_sha256"]
    )
    assert hashlib.sha256(manifest_bytes).hexdigest() == proof["games_sha256"]
    for name, digest in proof["implementation_sha256"].items():
        assert sha(ROOT / name) == digest, name
    assert (
        complete["updates"] == 30
        and complete["training_games"] == 240
        and complete["development_games"] == 64
    )
    assert (
        complete["frozen_endpoint_games"] == 280
        and complete["reused_raw_frozen_games"] == 280
    )
    assert complete["condition"] == "B" and complete["training_noise"] == 0.1
    assert (
        complete["initialization"] == "raw_base_no_sft"
        and complete["ledger_export_complete"]
        and complete["all_HTTP_work_drained"]
    )
    assert config["lora"]["seed"] == 41 and config["checkpoint_ttl_seconds"] is None
    assert config["reward"] == {
        "win": 1,
        "per_question": -0.03,
        "per_invalid": -0.1,
        "information_shaping": False,
    }
    for row in manifest["training"]:
        r = row["record"]
        assert r == training_game(r["n"], 1000000 + row["update"], seed=41, noise=0.1)
        assert set(r["world"]["names"]) <= set(load_split()["train"])
    expected = {
        r["id"]: r
        for c in frozen_manifest()["cells"]
        for r in frozen_games(c["domain"], c["n"], c["noise"], 28)
    }
    assert expected == {r["id"]: r for r in manifest["evaluation"]}
    frozen = ROOT / "evals/frozen"
    for cell in json.loads((frozen / "manifest.json").read_text())["cells"]:
        assert sha(frozen / cell["file"]) == cell["sha256"]
    unchanged = [
        "evals/frozen",
        "evals/candidate_set",
        "evals/hard_mode.json",
        "twenty_bits/game.py",
        "twenty_bits/predicates.py",
        "twenty_bits/candidate_feedback.py",
        "twenty_bits/learnability.py",
        "twenty_bits/prompts.py",
        "twenty_bits/worlds.py",
    ]
    assert not subprocess.check_output(
        ["git", "diff", "ea02327", "--name-only", "--", *unchanged], cwd=ROOT
    ).strip()
    events_proof = json.loads(
        (ROOT / "research/ledger_events_archive.json").read_text()
    )
    assert sha(ROOT / events_proof["archive"]) == events_proof["archive_sha256"]
    assert sha(ROOT / "ledger.json") == events_proof["ledger_json_sha256"]
    latest = {}
    for index, row in enumerate(read_rows(ROOT / events_proof["archive"]), 1):
        assert row["sequence"] == index and row["entry_id"] == row["entry"]["id"]
        latest[row["entry_id"]] = row["entry"]
    assert index == events_proof["events"]
    assert len(latest) == events_proof["entries"]
    assert (
        list(latest.values()) == Ledger.read_snapshot(ROOT / "ledger.json")["entries"]
    )
    current = Ledger.read_snapshot(ROOT / "ledger.json")
    status = Ledger.snapshot_status(ROOT / "ledger.json")
    entries = {e["id"]: e for e in current["entries"]}
    previous = json.loads(
        subprocess.check_output(["git", "show", "705a2b5:ledger.json"], cwd=ROOT)
    )
    assert all(entries[e["id"]] == e for e in previous["entries"])
    assert (
        previous["approvals"] == current["approvals"]
        and current["cap_usd"] == "50.000000"
    )
    assert not status["blocked"]
    requests = read_rows(out / "requests.jsonl.gz")
    ops = read_rows(out / "operations.jsonl.gz")
    excluded = read_rows(out / "excluded_originals.jsonl.gz")
    assert len(ops) == 93 and sorted(
        int(o["request_id"].rsplit(":", 1)[1]) for o in ops
    ) == list(range(93))
    assert all(
        o["request_id"].rsplit(":", 1)[0] == complete["training_model_id"] for o in ops
    )
    assert not any("load" in o["key"] for o in ops)
    storage = [o for o in ops if o["storage"]]
    assert len(storage) == 2
    for r in requests + ops:
        entry = entries[r["entry_id"]]
        assert r["request_id_saved_before_dispatch"]
        assert entry["request_id"] == r["request_id"] == r["receipt"]["request_id"]
        assert (
            entry["created_at"]
            <= r["saved_before_dispatch_at"]
            <= r["collection_started_at"]
            <= r["response_received_at"]
        )
        if r.get("storage"):
            assert r["completed"] and r["payload"]["ttl_seconds"] is None
            assert (
                entry["state"] in ACTIVE_STATES
                and entry["checkpoint"]["expires_at"] is None
            )
        else:
            assert r["settled"] and Decimal(entry["actual_usd"]) == Decimal(
                r["actual_usd"]
            )
    registry = json.loads((ROOT / "research/main_B41_replacements.json").read_text())
    excluded_ids = {r["entry_id"] for r in excluded}
    assert len(excluded_ids) == len(registry["cases"])
    cases = []
    for case in registry["cases"]:
        original = next(
            r for r in excluded if r["entry_id"] == case["original_entry_id"]
        )
        replacement = next(
            r for r in requests if r["entry_id"] == case["replacement_entry_id"]
        )
        assert (
            original["orphaned"]
            and original["output_allowed"] is False
            and original["request_id_saved_before_dispatch"]
        )
        assert entries[original["entry_id"]]["state"] in ACTIVE_STATES
        assert original["signature"] == replacement["signature"] == case["signature"]
        assert (
            original["parameters"] == replacement["parameters"]
            and case["replacements_used"] == 1
        )
        cases.append(
            {**case, "original_hold_usd": entries[original["entry_id"]]["reserved_usd"]}
        )
    prior_active = {e["id"] for e in previous["entries"] if e["state"] in ACTIVE_STATES}
    assert {
        e["id"] for e in current["entries"] if e["state"] in ACTIVE_STATES
    } == prior_active | excluded_ids | {o["entry_id"] for o in storage}
    for kind, row in complete["checkpoints"]["30"].items():
        assert (
            row["checkpoint_type"] == kind
            and row["size_bytes"] > 0
            and row["expires_at"] is None
        )
        assert row["tinker_path"].startswith(
            "tinker://" + complete["training_model_id"] + "/"
        )
        assert any(
            entries[o["entry_id"]]["checkpoint"]["tinker_path"] == row["tinker_path"]
            for o in storage
        )
    assert json.loads((out / "sessions.json").read_text())["finished"]
    log = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    (out / "unit_tests.txt").write_text(log.stdout + log.stderr)
    tests = int(re.search(r"Ran (\d+) tests", log.stderr)[1])
    ledger_hash = sha(ROOT / "ledger.json")
    with (
        patch.object(
            PilotTransport,
            "open",
            side_effect=AssertionError("Completed runners must not contact Tinker"),
        ),
        redirect_stdout(io.StringIO()),
    ):
        asyncio.run(run_main_B41.main())
        run_B41_stage.main()
    assert sha(ROOT / "ledger.json") == ledger_hash
    result = {
        "tests_passed": tests,
        "sampling_requests_verified": len(requests),
        "mutation_requests_verified": len(ops),
        "gradient_batches_reconstructed": 30,
        "native_training_and_sampler_no_expiry": True,
        "previous_entries_approvals_and_holds_unchanged": True,
        "frozen_hashes_unchanged": True,
        "frozen_games_in_gradients": 0,
        "training_pool_only": True,
        "training_noise": 0.1,
        "fresh_provider_base": True,
        "replacement_cases": cases,
        "completed_runner_service_calls": 0,
        "all_HTTP_work_drained": True,
        "raw_run_cache_present_during_verification": (ROOT / "runs").exists(),
        "live_database_present_during_verification": (ROOT / "ledger.sqlite3").exists(),
    }
    (out / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    files = [p for p in out.glob("*.json*") if p.name != "reproduction.json"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in files}
    original_glob = Path.glob

    def archives_only(path, pattern):
        return (
            iter(())
            if path.is_relative_to(ROOT / "runs")
            else original_glob(path, pattern)
        )

    with patch.object(Path, "glob", archives_only), redirect_stdout(io.StringIO()):
        analyze_main_B41.main()
        analyze_all_main_seeds.main()
    assert all(sha(ROOT / name) == digest for name, digest in before.items())
    assert sha(ROOT / "ledger.json") == ledger_hash
    (out / "reproduction.json").write_text(
        json.dumps(
            {
                "archives_only_analysis_identical": True,
                "service_calls": 0,
                "uses_completed_ledger_export": True,
                "sha256": before,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "replacement_cases"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
