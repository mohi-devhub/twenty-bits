"""Measure real chat-template inputs and played trajectories without any service."""

from pathlib import Path
import gzip
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from threadpoolctl import threadpool_limits
from twenty_bits.worlds import ROOT, sample_game
from twenty_bits.prompts import get_tokenizer, prompt_ids
from twenty_bits.baselines import play

MODELS = ["Qwen/Qwen3-8B", "Qwen/Qwen3.5-4B", "openai/gpt-oss-120b"]


def stats(values):
    return {
        "mean": float(np.mean(values)),
        "p95": float(np.quantile(values, 0.95)),
        "min": int(min(values)),
        "max": int(max(values)),
    }


def main():
    manifest = json.loads((ROOT / "evals/frozen/manifest.json").read_text())
    report = {
        "thinking": "disabled for Qwen chat templates; gpt-oss thinking remains possible and must be capped",
        "models": {},
        "trajectory_measurements": [],
    }
    with threadpool_limits(limits=1):
        for model in MODELS:
            tokenizer = get_tokenizer(model)
            cells = []
            for cell in manifest["cells"]:
                games = [
                    json.loads(line)
                    for line in gzip.decompress(
                        (ROOT / "evals/frozen" / cell["file"]).read_bytes()
                    )
                    .decode()
                    .splitlines()
                ]
                counts = [len(prompt_ids(r, model=model)) for r in games]
                row = {k: cell[k] for k in ["domain", "n", "noise"]}
                row["initial_prompt_tokens"] = stats(counts)
                # Measured valid trajectories use a declared 8-game slice,
                # distinct from the 200-game token count coverage above.
                for r in games[:8]:
                    trace = play(
                        r, "greedy_predicate", tokenizer=tokenizer, keep_trace=True
                    )
                    counts_turn = [
                        len(prompt_ids(r, trace["turns"][:j], model))
                        for j in range(len(trace["turns"]))
                    ]
                    outputs = [
                        len(tokenizer.encode(t["action"], add_special_tokens=False))
                        for t in trace["turns"]
                    ]
                    report["trajectory_measurements"].append(
                        {
                            "model": model,
                            "domain": cell["domain"],
                            "n": cell["n"],
                            "noise": cell["noise"],
                            "index": len(report["trajectory_measurements"]) % 8,
                            "input_tokens": sum(counts_turn),
                            "output_tokens": sum(outputs),
                            "turns": len(outputs),
                            "initial_tokens": counts_turn[0],
                            "max_prompt_tokens": max(counts_turn),
                            "action_tokens_per_turn": outputs,
                            "questions": trace["questions"],
                        }
                    )
                cells.append(row)
                print(
                    model,
                    cell["domain"],
                    cell["n"],
                    cell["noise"],
                    row["initial_prompt_tokens"],
                    flush=True,
                )
            report["models"][model] = {"cells": cells}
    for domain in ["animals", "tools", "foods", "synthetic"]:
        for n in [16, 32, 64, 128, 256]:
            r = sample_game(domain, n, 0, namespace="token-audit-v1", noise=0)
            report.setdefault("offline_grid_prompt_examples", []).append(
                {"domain": domain, "n": n, "tokens": len(prompt_ids(r))}
            )
    # Prefix reuse is measured on exact token IDs, not assumed from text.
    a = sample_game("animals", 32, 0, namespace="paid-v1", noise=0)
    b = sample_game("animals", 32, 0, namespace="paid-v1", noise=0.1)
    report["stable_prefix"] = {}
    for model in MODELS:
        aa, bb = prompt_ids(a, model=model), prompt_ids(b, model=model)
        shared = next(
            (i for i, (x, y) in enumerate(zip(aa, bb)) if x != y), min(len(aa), len(bb))
        )
        report["stable_prefix"][model] = {
            "shared_tokens_across_noise_modes": shared,
            "total_noiseless_tokens": len(aa),
        }
    (ROOT / "research/token_measurements.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
