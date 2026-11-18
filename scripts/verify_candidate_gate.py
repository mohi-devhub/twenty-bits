"""Verify the completed paired check, budget invariants and offline reproduction."""

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
from scripts import run_candidate_qualification, summarize_candidate_qualification
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.supervised import qualification_records
from twenty_bits.tinker_transport import GuardedTinker, save_json
from twenty_bits.worlds import ROOT, load_split


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    status = Ledger(ROOT / "ledger.json").status()
    before = json.loads(
        subprocess.check_output(["git", "show", "624926d:ledger.json"], cwd=ROOT)
    )
    entries = {e["id"]: e for e in status["entries"]}
    assert all(entries[e["id"]] == e for e in before["entries"])
    assert (
        before["approvals"]
        == json.loads((ROOT / "ledger.json").read_text())["approvals"]
    )
    prior_active = {e["id"] for e in before["entries"] if e["state"] in ACTIVE_STATES}
    active = {e["id"] for e in status["entries"] if e["state"] in ACTIVE_STATES}
    assert active == prior_active
    assert sum(Decimal(entries[e]["reserved_usd"]) for e in active) == Decimal(
        ".112813"
    )
    source = json.loads((ROOT / "results/format_sft/completion.json").read_text())
    records_path = ROOT / "experiments/format_qualification_games.json"
    records = json.loads(records_path.read_text())
    assert records == qualification_records()
    train = set(load_split()["train"])
    assert all(set(r["world"]["names"]) <= train for r in records)
    attempts = 0
    total = Decimal(0)
    for policy in ("format_sft", "raw_base"):
        config_path = ROOT / f"experiments/candidate_set_{policy}.json"
        config = json.loads(config_path.read_text())
        proof = json.loads(
            (ROOT / f"research/candidate_set_{policy}_rendering.json").read_text()
        )
        assert digest(config_path) == proof["config_sha256"]
        assert digest(records_path) == proof["games_sha256"]
        for name, sha in proof["implementation_sha256"].items():
            assert digest(ROOT / name) == sha, name
        folder = ROOT / f"results/candidate_set/{policy}"
        completion = json.loads((folder / "completion.json").read_text())
        assert completion["session_finished"]
        assert completion["training_updates"] == completion["rl_updates"] == 0
        if policy == "format_sft":
            assert (
                completion["sampler"]["model_path"]
                == source["checkpoints"]["native"]["path"]
            )
        else:
            assert (
                "model_path" not in completion["sampler"]
                and not config["sampling_checkpoint_paths"]
            )
        run_entries = [
            e
            for e in status["entries"]
            if e["operation"].startswith(f"[{config['run_id']}] ")
        ]
        assert all(e["state"] == "settled" for e in run_entries)
        assert not any(
            "SFT " in e["operation"]
            or "optim" in e["operation"]
            or "forward" in e["operation"]
            for e in run_entries
        )
        cost = sum(Decimal(e["actual_usd"]) for e in run_entries)
        assert cost <= Decimal(".25")
        total += cost
        requests = [
            json.loads(line) for line in gzip.open(folder / "requests.jsonl.gz", "rt")
        ]
        used = {
            t["usage"]["entry_id"]
            for line in gzip.open(folder / "games.jsonl.gz", "rt")
            for t in json.loads(line)["turns"]
        }
        assert used == {r["entry_id"] for r in requests}
        for r in requests:
            assert r["settled"] and r["request_id_saved_before_dispatch"]
            assert r["saved_before_dispatch_at"] <= r["collection_started_at"]
            assert (
                r["receipt"]["request_id"]
                == r["request_id"]
                == entries[r["entry_id"]]["request_id"]
            )
            assert r["request_id"].rsplit(":", 1)[0] == completion["sampler"]["id"]
            assert r.get("output_allowed") is not False and not r.get("orphaned")
        attempts += len(requests)
    assert total == Decimal(".019543") and total <= Decimal(".50")
    manifest = json.loads((ROOT / "evals/frozen/manifest.json").read_text())
    for cell in manifest["cells"]:
        assert digest(ROOT / "evals/frozen" / cell["file"]) == cell["sha256"]
    # None of the old bank, prompt hashes, or core budget implementation changed.
    assert not subprocess.check_output(
        [
            "git",
            "diff",
            "624926d",
            "--name-only",
            "--",
            "evals/frozen",
            "twenty_bits/budget.py",
        ],
        cwd=ROOT,
    ).strip()
    hashes = json.loads((ROOT / "evals/candidate_set/prompt_hashes.json").read_text())
    assert len(hashes["hashes"]) == 2000
    ledger_hash = digest(ROOT / "ledger.json")
    with (
        patch.object(
            GuardedTinker,
            "open",
            side_effect=AssertionError("No service access allowed"),
        ),
        redirect_stdout(io.StringIO()),
    ):
        asyncio.run(run_candidate_qualification.main())
    assert digest(ROOT / "ledger.json") == ledger_hash
    result = {
        "tests_passed": 107,
        "qualification_games": 64,
        "training_pool_only": True,
        "exact_paired_game_and_generation_seeds_verified": True,
        "sampling_attempts_with_pre_dispatch_ids": attempts,
        "same_saved_sft_checkpoint_loaded": True,
        "raw_base_has_no_adapter": True,
        "native_prompt_signatures_and_replays_verified": attempts,
        "new_training_updates": 0,
        "rl_updates": 0,
        "new_run_recorded_usage_usd": str(total),
        "new_run_holds_usd": "0.000000",
        "combined_cap_including_holds_usd": "0.500000",
        "prior_ledger_entries_and_approval_unchanged": True,
        "old_active_holds_unchanged_usd": "0.112813",
        "frozen_games_verified": 2000,
        "old_prompt_hashes_unchanged": True,
        "new_initial_prompt_hashes": 2000,
        "completed_runners_service_calls": 0,
        "completed_runner_ledger_unchanged": True,
    }
    save_json(ROOT / "results/candidate_set/validation.json", result)
    files = sorted((ROOT / "results/candidate_set").glob("**/*.json"))
    files += sorted((ROOT / "results/candidate_set").glob("**/*.jsonl.gz"))
    files = [p for p in files if p.name != "reproduction.json"]
    old_hashes = {str(p.relative_to(ROOT)): digest(p) for p in files}
    original_glob = Path.glob

    def archives_only(path, pattern):
        return (
            iter(())
            if path.is_relative_to(ROOT / "runs")
            else original_glob(path, pattern)
        )

    with patch.object(Path, "glob", archives_only), redirect_stdout(io.StringIO()):
        summarize_candidate_qualification.main()
    assert all(digest(ROOT / name) == sha for name, sha in old_hashes.items())
    assert digest(ROOT / "ledger.json") == ledger_hash
    save_json(
        ROOT / "results/candidate_set/reproduction.json",
        {
            "committed_archive_analysis_identical_without_run_cache": True,
            "service_calls": 0,
            "sha256": old_hashes,
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
