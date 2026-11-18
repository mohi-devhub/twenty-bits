"""Candidate-set observations derived only from public answers and the table."""

import hashlib
import json

import numpy as np

from .learnability import probe_messages

PROMPT_VERSION = "candidate-set-v1"
POSTERIOR_THRESHOLD = 0.001
FEEDBACK_RULES = """
ENVIRONMENT STATE FEEDBACK
After each answer, including INVALID, the environment supplies candidate names.
With no answer noise, REMAINING CANDIDATES is the exact consistent set.
With answer noise, POSTERIOR CANDIDATES lists items with posterior probability
strictly above 0.001, plus the top candidate. TOP CANDIDATE is the maximum-posterior
item; ties use TABLE order. The noisy list is approximate: excluded items can
reappear after later answers. A list with one item does not prove certainty in
noisy mode. The full original TABLE stays available for every legal question.
"""


def feedback(record: dict, posterior: list[float]) -> dict:
    names = record["world"]["names"]
    mass = np.asarray(posterior, dtype=float)
    if (
        mass.shape != (len(names),)
        or not np.isfinite(mass).all()
        or (mass < 0).any()
        or not np.isclose(mass.sum(), 1, atol=1e-12, rtol=0)
    ):
        raise ValueError("Candidate feedback needs a normalized posterior.")
    if record["noise"] == 0:
        indices = np.flatnonzero(mass > 0).tolist()
        return {"kind": "exact", "candidates": [names[i] for i in indices]}
    if record["noise"] != 0.10:
        raise ValueError("Unsupported answer noise.")
    top = int(np.argmax(mass))
    indices = [i for i, p in enumerate(mass) if p > POSTERIOR_THRESHOLD or i == top]
    return {
        "kind": "posterior_threshold",
        "threshold": POSTERIOR_THRESHOLD,
        "candidates": [names[i] for i in indices],
        "top_candidate": names[top],
    }


def feedback_text(state: dict) -> str:
    label = (
        "REMAINING CANDIDATES"
        if state["kind"] == "exact"
        else "POSTERIOR CANDIDATES (probability > 0.001, plus top)"
    )
    result = label + ": " + json.dumps(state["candidates"], separators=(",", ":"))
    if state["kind"] != "exact":
        result += "\nTOP CANDIDATE: " + state["top_candidate"]
    return result


def candidate_messages(record: dict, turns: list[dict] | None = None) -> list[dict]:
    public = probe_messages(record, turns)
    # Keep one stable rules/table prefix. Historical prompts are never modified.
    public[0]["content"] += FEEDBACK_RULES
    for i, turn in enumerate(turns or []):
        if turn["is_question"]:
            public[3 + 2 * i]["content"] += "\n" + feedback_text(
                feedback(record, turn["posterior_after"])
            )
    return public


def token_hash(ids: list[int]) -> str:
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
