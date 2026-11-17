"""Run all 120 baseline cells on paired deterministic offline games."""

from pathlib import Path
import argparse
import csv
import gzip
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from threadpoolctl import threadpool_limits
from twenty_bits.worlds import ROOT, sample_game
from twenty_bits.baselines import play
from twenty_bits.prompts import get_tokenizer
from twenty_bits.provenance import check_baseline_provenance

POLICIES = ["random", "greedy_single", "greedy_predicate"]


def summarize(games: list[dict], *, bootstrap: int = 2000) -> dict:
    rng = np.random.default_rng(3301)
    matrix = np.array(
        [
            [
                g["won"],
                g["questions"] * g["won"],
                g["questions"],
                sum(g["question_eigs"]),
                g["enumeration_count"],
                g["predicate_tokens"],
                g["invalid_count"],
                g["reasks_after_low_probability"],
                g["low_probability_opportunities"],
            ]
            for g in games
        ],
        dtype=float,
    )

    def values(t):
        win, wq, q, eig, enum, tokens, invalid, reasks, opportunities = t
        return [
            win / len(games),
            wq / win if win else np.nan,
            eig / q if q else np.nan,
            enum / q if q else np.nan,
            tokens / q if q else np.nan,
            invalid / q if q else np.nan,
            reasks / opportunities if opportunities else np.nan,
        ]

    aggregate = values(matrix.sum(axis=0))
    samples = np.array(
        [
            values(matrix[rng.integers(0, len(games), len(games))].sum(axis=0))
            for _ in range(bootstrap)
        ]
    )
    names = [
        "win_rate",
        "questions_per_win",
        "eig_per_question",
        "enumeration_rate",
        "predicate_tokens",
        "invalid_rate",
        "reask_after_low_probability_rate",
    ]
    out = {
        "games": len(games),
        "questions": int(matrix[:, 2].sum()),
        "low_probability_opportunities": int(matrix[:, 8].sum()),
    }
    for j, name in enumerate(names):
        valid = samples[:, j][np.isfinite(samples[:, j])]
        out[name] = float(aggregate[j]) if np.isfinite(aggregate[j]) else None
        out[name + "_ci95"] = (
            [float(x) for x in np.quantile(valid, [0.025, 0.975])]
            if len(valid)
            else None
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games-per-cell", type=int, default=200)
    parser.add_argument(
        "--output-directory", type=Path, default=ROOT / "results/baselines"
    )
    args = parser.parse_args()
    destination = args.output_directory
    destination.mkdir(parents=True, exist_ok=True)
    check_baseline_provenance(destination, "offline-v1", args.games_per_cell)
    tokenizer = get_tokenizer()
    summaries = []
    with threadpool_limits(limits=1):
        for domain in ["animals", "tools", "foods", "synthetic"]:
            for n in [16, 32, 64, 128, 256]:
                for noise in [0, 0.1]:
                    path = destination / f"{domain}_n{n}_p{noise:.2f}.jsonl.gz"
                    if path.exists():
                        records = [
                            json.loads(line)
                            for line in gzip.decompress(path.read_bytes())
                            .decode()
                            .splitlines()
                        ]
                        if len(records) != args.games_per_cell * 3:
                            raise RuntimeError(
                                "Existing results use another sample count."
                            )
                    else:
                        records = []
                        for i in range(args.games_per_cell):
                            game = sample_game(
                                domain, n, i, namespace="offline-v1", noise=noise
                            )
                            for policy in POLICIES:
                                records.append(play(game, policy, tokenizer=tokenizer))
                        content = "".join(
                            json.dumps(r, separators=(",", ":")) + "\n" for r in records
                        ).encode()
                        path.write_bytes(gzip.compress(content, mtime=0))
                    for policy in POLICIES:
                        row = {
                            "domain": domain,
                            "n": n,
                            "noise": noise,
                            "policy": policy,
                            **summarize([r for r in records if r["policy"] == policy]),
                        }
                        summaries.append(row)
                    print(
                        domain,
                        n,
                        noise,
                        [
                            (p, round(summaries[-3 + j]["win_rate"], 3))
                            for j, p in enumerate(POLICIES)
                        ],
                        flush=True,
                    )
                    (destination / "summary.json").write_text(
                        json.dumps(summaries, indent=2, allow_nan=False) + "\n"
                    )
    scalar = [
        {k: v for k, v in row.items() if not k.endswith("_ci95")} for row in summaries
    ]
    with (destination / "summary.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scalar[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(scalar)
    lines = [
        "# Offline baseline grid",
        "",
        f"{args.games_per_cell} paired games per cell. Intervals resample complete games, 2000 times. EIG includes losses and INVALID questions. Predicate length uses the pinned Qwen3-8B tokenizer. A dash means no eligible observations.",
        "",
        "| Domain | N | Noise | Policy | Win % | Questions/win | EIG/question | Predicate tokens | Enumeration % | Invalid % | Re-ask after unlikely % |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in summaries:

        def f(k, scale=1):
            return "—" if r[k] is None else f"{r[k] * scale:.3f}"

        lines.append(
            f"| {r['domain']} | {r['n']} | {r['noise']} | {r['policy']} | {f('win_rate', 100)} | {f('questions_per_win')} | {f('eig_per_question')} | {f('predicate_tokens')} | {f('enumeration_rate', 100)} | {f('invalid_rate', 100)} | {f('reask_after_low_probability_rate', 100)} |"
        )
    (destination / "BASELINES.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
