"""Finite table worlds, explicit row splits, and reproducible subsets."""

from __future__ import annotations
from dataclasses import dataclass
from functools import cache
import hashlib
import json
from pathlib import Path
import random
import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def seed_for(*parts: object) -> int:
    return int.from_bytes(
        hashlib.sha256(json.dumps(parts).encode()).digest()[:8], "big"
    )


@dataclass(frozen=True)
class World:
    domain: str
    attributes: tuple[str, ...]
    names: tuple[str, ...]
    rows: np.ndarray

    def __post_init__(self):
        if self.rows.shape != (len(self.names), len(self.attributes)):
            raise ValueError("World dimensions disagree.")
        if len(set(self.names)) != len(self.names) or len(set(self.attributes)) != len(
            self.attributes
        ):
            raise ValueError("Names and attributes must be distinct.")
        if not np.all((self.rows == 0) | (self.rows == 1)):
            raise ValueError("Attributes must be binary.")
        if len({tuple(row) for row in self.rows.tolist()}) != len(self.names):
            raise ValueError("Every item must have a unique attribute vector.")
        self.rows.setflags(write=False)

    def subset(self, indices: list[int]) -> World:
        if len(set(indices)) != len(indices):
            raise ValueError("A subset cannot repeat an item.")
        rows = self.rows[indices]
        varying = np.any(rows != rows[0], axis=0)
        return World(
            self.domain,
            tuple(a for a, keep in zip(self.attributes, varying) if keep),
            tuple(self.names[i] for i in indices),
            rows[:, varying].copy(),
        )

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "attributes": list(self.attributes),
            "names": list(self.names),
            "rows": self.rows.astype(int).tolist(),
        }

    @classmethod
    def from_dict(cls, record: dict) -> World:
        return cls(
            record["domain"],
            tuple(record["attributes"]),
            tuple(record["names"]),
            np.asarray(record["rows"], dtype=np.uint8),
        )


@cache
def load_world(domain: str) -> World:
    return World.from_dict(
        json.loads((ROOT / f"data/worlds/{domain}.json").read_text())
    )


@cache
def load_split() -> dict:
    return json.loads((ROOT / "data/worlds/animal_split.json").read_text())


def sample_game(
    domain: str, n: int, index: int, *, namespace: str, noise: float
) -> dict:
    world = load_world(domain)
    rng = random.Random(seed_for(namespace, domain, n, index, "subset"))
    pool = list(range(len(world.names)))
    if domain == "animals" and namespace.startswith("paid"):
        heldout = set(load_split()["held_out"])
        pool = [i for i, name in enumerate(world.names) if name in heldout]
    if domain == "animals" and namespace.startswith("train"):
        allowed = set(load_split()["train"])
        pool = [i for i, name in enumerate(world.names) if name in allowed]
    if n > len(pool):
        raise ValueError("Requested subset exceeds the available pool.")
    world = world.subset(rng.sample(pool, n))
    if domain == "synthetic":
        # New labels and column order on every game prevent fixed label meanings.
        columns = list(range(len(world.attributes)))
        rng.shuffle(columns)
        labels = rng.sample(range(100000, 999999), len(columns) + n)
        world = World(
            "synthetic_relabeled",
            tuple(f"a_{x}" for x in labels[: len(columns)]),
            tuple(f"s_{x}" for x in labels[len(columns) :]),
            world.rows[:, columns].copy(),
        )
    target = rng.randrange(n)
    return {
        "id": f"{namespace}/{domain}/{n}/{index}/p{noise}",
        "domain": domain,
        "n": n,
        "noise": noise,
        "noise_seed": seed_for(namespace, domain, n, index, "noise"),
        "target": target,
        "world": world.to_dict(),
    }


def training_game(n: int, index: int, *, seed: int, noise: float) -> dict:
    """Training has no domain argument: only the fixed animals pool is allowed."""
    if n not in (16, 32, 64, 128):
        raise ValueError("Training sizes must follow the 16 to 128 curriculum.")
    if noise not in (0, 0.10):
        raise ValueError("Training noise must be 0 or 0.10.")
    return sample_game(
        "animals", n, index, namespace=f"train-v1/seed{seed}", noise=noise
    )
