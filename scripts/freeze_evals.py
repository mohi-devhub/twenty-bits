"""Create an immutable 200-game-per-cell bank; plans choose declared slices."""

from pathlib import Path
import gzip
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT, sample_game

CELLS = [
    (domain, n, p)
    for domain, sizes in [("animals", [32, 128]), ("synthetic", [32, 128, 256])]
    for n in sizes
    for p in [0, 0.10]
]


def main():
    destination = ROOT / "evals/frozen"
    if (destination / "manifest.json").exists():
        raise SystemExit(
            "The bank already exists. Verify it; do not silently replace it."
        )
    cells = []
    for domain, n, p in CELLS:
        filename = f"{domain}_n{n}_p{p:.2f}.jsonl.gz"
        content = "".join(
            json.dumps(
                sample_game(domain, n, i, namespace="paid-v1", noise=p),
                separators=(",", ":"),
            )
            + "\n"
            for i in range(200)
        ).encode()
        blob = gzip.compress(content, mtime=0)
        (destination / filename).write_bytes(blob)
        cells.append(
            {
                "domain": domain,
                "n": n,
                "noise": p,
                "file": filename,
                "games": 200,
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )
    worlds = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "data/worlds").glob("*.json"))
    }
    (destination / "manifest.json").write_text(
        json.dumps(
            {
                "protocol": "v1",
                "namespace": "paid-v1",
                "cells": cells,
                "world_hashes": worlds,
                "training_exclusion": "all paid-v1 game IDs; all held-out animal rows; every tools, foods, synthetic row",
                "selection": "Plans use a common index slice starting at zero, identical for every checkpoint. No target-dependent selection.",
            },
            indent=2,
        )
        + "\n"
    )
    print("Frozen", len(cells), "cells and", sum(c["games"] for c in cells), "games.")


if __name__ == "__main__":
    main()
