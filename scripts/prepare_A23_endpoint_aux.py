"""Pin auxiliary frozen games and token sequences before A23 training starts."""

import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.prepare_rl_pilot import freeze
from twenty_bits.candidate_feedback import candidate_messages, token_hash
from twenty_bits.learnability import probe_messages
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    primary = json.loads((ROOT / "experiments/main_A23.json").read_text())
    manifest = json.loads(gzip.decompress((ROOT / "experiments/main_A23_games.json.gz").read_bytes()))
    hashes = json.loads((ROOT / "evals/candidate_set/prompt_hashes.json").read_text())["hashes"]
    registry = json.loads((ROOT / "research/main_A23_replacements.json").read_text())
    legacy = set(registry["legacy_lost_entry_ids"])
    legacy.update(c["original_entry_id"] for c in registry["cases"])
    files = ["scripts/run_A23_endpoint_aux.py", "twenty_bits/suffix_diagnostic.py",
             "twenty_bits/model_player.py", "twenty_bits/game.py", "twenty_bits/predicates.py",
             "twenty_bits/recovery.py", "twenty_bits/tinker_transport.py", "twenty_bits/budget.py",
             "twenty_bits/candidate_feedback.py", "twenty_bits/learnability.py",
             "twenty_bits/tinker_rendering.py", "twenty_bits/guess_metrics.py"]
    files.append("twenty_bits/replacement_registry.py")
    for mode in ("suffix", "hard"):
        config = {**primary, "run_id": f"A23-{mode}-v1",
            "display_name": f"Twenty Bits A23 {mode} auxiliary evaluation",
            "training_authorized": False, "rl_training_authorized": False,
            "is_primary_result": False, "diagnostic_only": mode == "suffix",
            "run_cap_usd": "1.500000" if mode == "suffix" else "2.050000",
            "sampling_seed_namespace": "main-U-v1/evaluation" if mode == "suffix" else "main-U-v1/hard-mode",
            "remaining_candidate_feedback": mode == "suffix",
            "observation_mode": "candidate_set" if mode == "suffix" else "no_candidate_list",
            "endpoint_source": "results/main_A23/primary_completion.json",
            "external_upload_or_export_required": False}
        records = [r for r in manifest["evaluation"] if r["domain"] == "synthetic"] if mode == "suffix" else [r for r in manifest["evaluation"] if int(r["id"].split("/")[-2]) in (0, 1)]
        assert len(records) == (168 if mode == "suffix" else 20)
        config_path = ROOT / f"experiments/A23_{mode}.json"
        freeze(config_path, config)
        games_path = ROOT / f"experiments/A23_{mode}_games.json"
        freeze(games_path, records)
        games_path.with_suffix(".json.gz").write_bytes(gzip.compress(games_path.read_bytes(), mtime=0))
        rendering = Rendering(config["primary_model"], config)
        prompts = []
        for record in records:
            builder = candidate_messages if mode == "suffix" else probe_messages
            ids = rendering.prompt(builder(record)).to_ints()
            expected = hashes[record["id"]]["main_initial_tokens_sha256" if mode == "suffix" else "hard_initial_tokens_sha256"]
            assert token_hash(ids) == expected
            assert len(ids) + config["primary_output_cap"] <= config["context_window"]
            if mode == "suffix":
                assert SuffixDiagnosticGame(record).aliases.extra
            prompts.append({"id": record["id"], "tokens": len(ids), "sha256": expected})
        save_json(ROOT / f"research/A23_{mode}_preflight.json", {
            "config_sha256": sha(config_path), "games_sha256": sha(games_path),
            "implementation_sha256": {p: sha(ROOT / p) for p in files},
            "native_tokenizer_parity": True, "prompts": prompts,
            "games_per_policy": len(records), "policies": 1 if mode == "suffix" else 2,
            "mode": mode, "is_primary_result": False, "service_calls": 0,
            "frozen_subset_target_noise_seeds_unchanged": True,
            "source_policy": "A23 scheduled endpoint; fresh client from native permanent sampler",
            "cap_including_holds_usd": config["run_cap_usd"]})
        p = ROOT / f"research/A23_{mode}_replacements.json"
        if not p.exists():
            save_json(p, {"legacy_lost_entry_ids": sorted(legacy), "cases": []})
        print(json.dumps({"mode": mode, "games_per_policy": len(records), "native_prompts": len(prompts), "cap": config["run_cap_usd"], "service_calls": 0}))


if __name__ == "__main__":
    main()
