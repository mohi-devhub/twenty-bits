"""Keep cached baseline results tied to their worlds, tokenizer, and seed scheme."""

import hashlib
import json
from pathlib import Path
from .worlds import ROOT


def baseline_provenance(namespace: str, games_per_cell: int) -> dict:
    inputs = list(sorted((ROOT / "data/worlds").glob("*.json"))) + [
        ROOT / "research/tokenizers.json"
    ]
    if namespace == "paid-v1":
        inputs.append(ROOT / "evals/frozen/manifest.json")
    return {
        "namespace": namespace,
        "games_per_cell": games_per_cell,
        "policies": ["random", "greedy_single", "greedy_predicate"],
        "predicate_tokenizer": "Qwen/Qwen3-8B",
        "input_hashes": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
        },
    }


def check_baseline_provenance(
    directory: Path, namespace: str, games_per_cell: int
) -> None:
    expected = baseline_provenance(namespace, games_per_cell)
    path = directory / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != expected:
        raise ValueError(
            "Cached baseline inputs changed. Use another output directory for a new sweep."
        )
    path.write_text(json.dumps(expected, indent=2) + "\n")
