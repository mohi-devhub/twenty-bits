"""Check completed paid artifacts against the exact game and spending record."""

from decimal import Decimal
from pathlib import Path
import gzip
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from twenty_bits.budget import Ledger
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.game import Game
from twenty_bits.worlds import ROOT, seed_for
from twenty_bits.tinker_transport import save_json
from twenty_bits.tinker_rendering import Rendering


def main():
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    directory = ROOT / "results/phase2"
    summary = json.loads((directory / "summary.json").read_text())
    if summary["status"] != "complete" or summary["completed_games"] != 300:
        raise ValueError("The approved evaluation is incomplete.")
    games = [
        json.loads(line)
        for line in gzip.decompress(
            (directory / "games.jsonl.gz").read_bytes()
        ).splitlines()
    ]
    records = {}
    for cell in frozen_manifest()["cells"]:
        for record in frozen_games(cell["domain"], cell["n"], cell["noise"], 28):
            records[record["id"]] = record
    status = Ledger(ROOT / "ledger.json").status()
    entries = {e["id"]: e for e in status["entries"]}
    incident = json.loads((ROOT / "research/phase2_incident.json").read_text())
    request_rows = [
        json.loads(line)
        for line in gzip.decompress(
            (directory / "requests.jsonl.gz").read_bytes()
        ).splitlines()
    ]
    journals = {
        row["key"]: row for row in request_rows if row["journal_kind"] == "requests"
    }
    by_entry = {row["entry_id"]: row for row in request_rows}
    orphan_ids = {r["entry_id"] for r in incident["original_orphaned_submissions"]}
    used = set()
    turns = 0
    context_losses = 0
    renderings = {
        model: Rendering(model, config)
        for model in (config["primary_model"], config["reference_model"])
    }
    cost = Decimal(0)
    for saved in games:
        game = Game(records[saved["game_id"]])
        for turn_index, turn in enumerate(saved["turns"]):
            journal = by_entry[turn["usage"]["entry_id"]]
            rendering = renderings[saved["model"]]
            prompt = rendering.observation(
                records[saved["game_id"]], saved["turns"][:turn_index]
            )
            payload = {
                "model": saved["model"],
                "prompt_ids": prompt.to_ints(),
                "sampling_params": journal["parameters"],
            }
            assert (
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                == journal["signature"]
            )
            assert prompt.length == turn["usage"]["prompt_tokens"]
            params = journal["parameters"]
            cap = (
                config["primary_output_cap"]
                if saved["model"] == config["primary_model"]
                else config["reference_output_cap"]
            )
            assert params["max_tokens"] == cap
            assert (
                params["temperature"] == config["temperature"]
                and params["top_p"] == config["top_p"]
                and params["top_k"] == config["top_k"]
            )
            assert params["stop"] == rendering.renderer.get_stop_sequences()
            assert params["seed"] == seed_for(
                config["sampling_seed_namespace"], saved["game_id"], turn_index
            ) % (2**31)
            result = game.step(
                turn["raw_action"],
                reasoning_tokens=turn["reasoning_tokens"],
                action_tokens=turn["action_tokens"],
                predicate_tokens=turn["predicate_tokens"],
                truncated=turn["truncated"],
            )
            assert result["answer"] == turn["answer"]
            assert result["invalid"] == turn["invalid"]
            assert abs(result["eig"] - turn["eig"]) < 1e-12
            np.testing.assert_allclose(
                result["posterior_after"],
                turn["posterior_after"],
                rtol=1e-12,
                atol=1e-14,
            )
            usage = turn["usage"]
            entry_id = usage["entry_id"]
            assert entry_id not in orphan_ids and entry_id not in used
            used.add(entry_id)
            assert entries[entry_id]["state"] == "settled"
            assert entries[entry_id]["actual_usd"] == usage["actual_usd"]
            assert entries[entry_id]["request_id"] == usage["request_id"]
            assert (
                turn["reasoning_tokens"]
                + turn["action_tokens"]
                + turn["control_tokens"]
                == usage["output_tokens"]
            )
            cost += Decimal(usage["actual_usd"])
            turns += 1
        if saved["context_overflow"]:
            cap = (
                config["primary_output_cap"]
                if saved["model"] == config["primary_model"]
                else config["reference_output_cap"]
            )
            assert (
                renderings[saved["model"]]
                .observation(records[saved["game_id"]], saved["turns"])
                .length
                + cap
                > config["context_window"]
            )
            game.done = True
            context_losses += 1
        assert game.done and game.won == saved["won"]
        assert game.questions == saved["questions"] <= game.limit
    assert cost == Decimal(status["spent_usd"])
    assert len(orphan_ids) == 5
    assert sum(Decimal(entries[e]["reserved_usd"]) for e in orphan_ids) == Decimal(
        "0.007195"
    )
    for entry_id in orphan_ids:
        assert entries[entry_id]["incident_status"] == "orphaned, possibly billed"
        assert not entries[entry_id]["output_allowed"]
        assert entries[entry_id]["state"] in {"dispatching", "submitted"}
    pending = {
        e["id"]
        for e in status["entries"]
        if e["state"] in {"dispatching", "submitted", "reserved"}
    }
    assert pending == orphan_ids
    before = after = 0
    for journal in journals.values():
        if journal["entry_id"] in orphan_ids:
            assert journal["orphaned"] and not journal["output_allowed"]
            continue
        if journal.get("request_id_saved_before_dispatch"):
            assert journal["request_id"] == journal["receipt"]["request_id"]
            assert "saved_before_dispatch_at" in journal
            assert entries[journal["entry_id"]]["request_id"] == journal["request_id"]
            after += 1
        else:
            before += 1
    assert before == incident["accepted_calls_before_this_rule"]
    for old_key, new_key in incident["approved_replacements"].items():
        old = journals[old_key]
        new = journals[new_key]
        assert old["signature"] == new["signature"] and old["orphaned"]
        assert new["settled"] and new["entry_id"] not in orphan_ids
    for row in request_rows:
        if row.get("confirmed_not_accepted"):
            assert row["signature"] == journals[row["key"]]["signature"]
    proof = {
        "games_replayed": len(games),
        "turns_replayed": turns,
        "submitted_token_sequences_and_sampling_settings_reconstructed": turns,
        "new_calls_with_id_saved_before_dispatch_and_matching_receipt": after,
        "accepted_calls_before_write_ahead_id_change": before,
        "replacement_prompt_and_seed_signatures_equal": len(
            incident["approved_replacements"]
        ),
        "orphaned_outputs_used": 0,
        "context_limit_losses_verified": context_losses,
        "orphaned_holds_usd": "0.007195",
        "actual_usage_cost_usd": str(cost),
        "unexpected_pending_entries": 0,
        "no_training_operations": not any(
            "train" in e["operation"].lower() for e in status["entries"]
        ),
        "frozen_bank_sha256": hashlib.sha256(
            (ROOT / "evals/frozen/manifest.json").read_bytes()
        ).hexdigest(),
    }
    assert proof["no_training_operations"]
    save_json(directory / "verification.json", proof)
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
