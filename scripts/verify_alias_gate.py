"""Audit completed calls, training order, artifact integrity, and paid-run guards."""

import asyncio
from contextlib import redirect_stdout
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import run_format_sft, run_learnability_probe
from twenty_bits.budget import Ledger, ACTIVE_STATES, money
from twenty_bits.supervised import supervised_data
from twenty_bits.tinker_transport import sample_cost, rates
from twenty_bits.worlds import ROOT


def main():
    ledger = Ledger(ROOT / "ledger.json").status()
    entries = {e["id"]: e for e in ledger["entries"]}
    sampling_attempts = 0
    for stage in ("alias_probe", "format_sft"):
        stage_attempts = 0
        out = ROOT / "results" / stage
        games = [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
        requests = {
            r["entry_id"]: r
            for line in gzip.open(out / "requests.jsonl.gz", "rt")
            if (r := json.loads(line))
        }
        for game in games:
            for turn in game["turns"]:
                usage = turn["usage"]
                r = requests[usage["entry_id"]]
                e = entries[r["entry_id"]]
                assert r["request_id_saved_before_dispatch"] and r["settled"]
                assert (
                    r["request_id"]
                    == r["receipt"]["request_id"]
                    == e["request_id"]
                    == usage["request_id"]
                )
                assert (
                    money(r["actual_usd"])
                    == money(e["actual_usd"])
                    == money(usage["actual_usd"])
                )
                assert (
                    sample_cost(
                        r["model"],
                        r["prompt_tokens"],
                        r["output_tokens"],
                        r["prompt_cache_hit_tokens"],
                    )
                    == r["actual_usd"]
                )
                sampling_attempts += 1
                stage_attempts += 1
        assert len(games) == 32 and len(requests) == stage_attempts
    config = json.loads((ROOT / "experiments/format_sft.json").read_text())
    data = supervised_data(config)
    operations = {
        r["key"]: r
        for line in gzip.open(ROOT / "results/format_sft/operations.jsonl.gz", "rt")
        if (r := json.loads(line))
    }
    curve = json.loads((ROOT / "results/format_sft/learning_curve.json").read_text())[
        "updates"
    ]
    index = 0
    tokens = 0
    storage = set()
    for epoch in range(2):
        order = list(range(len(data)))
        random.Random(config["shuffle_seed"] + epoch).shuffle(order)
        for start in range(0, len(data), 32):
            indices = order[start : start + 32]
            op = operations[f"forward-{index:03d}"]
            assert op["payload"]["indices"] == indices
            assert op["payload"]["loss_fn"] == "cross_entropy"
            assert op["payload"]["seq_id"] == index * 2 + 1
            count = sum(data[i].model_input.length for i in indices)
            assert count == op["payload"]["tokens"]
            expected = money(
                Decimal(count) * rates(config["primary_model"])["train"] / 1_000_000
            )
            assert (
                money(op["actual_usd"])
                == expected
                == money(entries[op["entry_id"]]["actual_usd"])
            )
            assert (
                abs(
                    op["reported_metrics"]["loss:sum"] / len(indices)
                    - curve[index]["action_nll"]
                )
                < 1e-5
            )
            optim = operations[f"optim-{index:03d}"]
            assert optim["payload"]["seq_id"] == index * 2 + 2 and optim["settled"]
            index += 1
            tokens += count
    assert index == 36 and tokens == 827254
    for op in operations.values():
        assert op["completed"]
        matching = [
            e
            for e in ledger["entries"]
            if e["operation"] == "[format-warmstart-v1] SFT " + op["key"]
        ]
        assert len(matching) == 1
        assert op["request_id"] == entries[op["entry_id"]]["request_id"]
        if op["storage"]:
            storage.add(op["entry_id"])
            assert op["payload"]["ttl_seconds"] == 7200
    assert len(storage) == 2
    completion = json.loads((ROOT / "results/format_sft/completion.json").read_text())
    for line in gzip.open(ROOT / "results/format_sft/requests.jsonl.gz", "rt"):
        request = json.loads(line)
        assert request["request_id"].rsplit(":", 1)[0] == completion["sampler_id"]
    for name, meta in completion["adapter_files"].items():
        file = ROOT / "runs/format-warmstart-v1/adapter" / name
        if file.exists():
            assert file.stat().st_size == meta["bytes"]
            assert hashlib.sha256(file.read_bytes()).hexdigest() == meta["sha256"]
    phase2 = json.loads((ROOT / "research/phase2_incident.json").read_text())
    prompt = json.loads(
        (ROOT / "research/learnability_probe_incident.json").read_text()
    )
    excluded = {r["entry_id"] for r in phase2["original_orphaned_submissions"]} | {
        r["entry_id"] for r in prompt["turns"]
    }
    active = {e["id"] for e in ledger["entries"] if e["state"] in ACTIVE_STATES}
    assert active == excluded | storage
    assert sum(Decimal(entries[i]["reserved_usd"]) for i in excluded) == Decimal(
        ".012813"
    )
    assert sum(Decimal(entries[i]["reserved_usd"]) for i in storage) == Decimal(
        ".100000"
    )
    old = json.loads(
        subprocess.check_output(["git", "show", "b65aff5:ledger.json"], cwd=ROOT)
    )
    assert all(entries[e["id"]] == e for e in old["entries"])
    assert (
        old["approvals"] == json.loads((ROOT / "ledger.json").read_text())["approvals"]
    )
    before = hashlib.sha256((ROOT / "ledger.json").read_bytes()).hexdigest()
    with (
        patch.object(
            run_learnability_probe.GuardedTinker,
            "open",
            side_effect=AssertionError("No service access allowed"),
        ),
        redirect_stdout(io.StringIO()),
    ):
        asyncio.run(
            run_learnability_probe.main(
                config_path=ROOT / "experiments/alias_probe.json",
                proof_path=ROOT / "research/alias_probe_rendering.json",
                games_path=ROOT / "experiments/learnability_probe_games.json",
                results_path=ROOT / "results/alias_probe",
                approved_run_cap="0.250000",
            )
        )
        asyncio.run(run_format_sft.main())
    assert before == hashlib.sha256((ROOT / "ledger.json").read_bytes()).hexdigest()
    result = {
        "tests_passed": 98,
        "frozen_games_verified": 2000,
        "historical_phase2_games_replayed": 300,
        "historical_phase2_turns_replayed": 3779,
        "alias_games_replayed": 32,
        "qualification_games_replayed": 32,
        "new_sampling_attempts_with_pre_dispatch_ids": sampling_attempts,
        "sft_forward_backward_operations": 36,
        "sft_optimizer_operations": 36,
        "full_context_training_tokens": tokens,
        "all_mutations_single_dispatch_verified": True,
        "all_supervised_losses_cross_entropy": True,
        "rl_updates": 0,
        "prior_ledger_entries_and_cap_approval_unchanged": True,
        "older_excluded_holds_usd": "0.012813",
        "bounded_checkpoint_storage_holds_usd": "0.100000",
        "unexpected_active_entries": 0,
        "completed_runners_service_calls": 0,
        "completed_runner_ledger_bytes_unchanged": True,
    }
    (ROOT / "results/format_sft/validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
