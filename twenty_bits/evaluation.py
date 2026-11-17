"""Load frozen games only after checking their bytes and world provenance."""

from __future__ import annotations
import gzip
import hashlib
import json
from .worlds import ROOT, World
from .prompts import messages


def frozen_manifest() -> dict:
    directory = ROOT / "evals/frozen"
    manifest = json.loads((directory / "manifest.json").read_text())
    protocol = json.loads((ROOT / "evals/protocol.json").read_text())
    if (
        hashlib.sha256((directory / "prompt_hashes.json").read_bytes()).hexdigest()
        != protocol["prompt_hashes_sha256"]
    ):
        raise ValueError("Frozen prompt hashes changed.")
    for name, digest in manifest["world_hashes"].items():
        if (
            hashlib.sha256((ROOT / "data/worlds" / name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError(f"World changed after freezing: {name}")
    return manifest


def frozen_games(domain: str, n: int, noise: float, count: int = 200) -> list[dict]:
    manifest = frozen_manifest()
    cell = next(
        c
        for c in manifest["cells"]
        if (c["domain"], c["n"], c["noise"]) == (domain, n, noise)
    )
    if not 0 < count <= cell["games"]:
        raise ValueError("Requested evaluation slice exceeds the frozen bank.")
    raw = (ROOT / "evals/frozen" / cell["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != cell["sha256"]:
        raise ValueError("Frozen game file changed.")
    records = [json.loads(line) for line in gzip.decompress(raw).decode().splitlines()]
    if len(records) != cell["games"]:
        raise ValueError("Frozen game count changed.")
    hashes = json.loads((ROOT / "evals/frozen/prompt_hashes.json").read_text())
    for record in records[:count]:
        World.from_dict(record["world"])
        prompt_hash = hashlib.sha256(
            json.dumps(messages(record), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if prompt_hash != hashes[record["id"]]:
            raise ValueError("The public prompt changed after freezing.")
    return records[:count]
