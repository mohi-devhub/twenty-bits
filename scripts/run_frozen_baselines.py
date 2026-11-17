"""Algorithmic references on the exact frozen games used in the paid plans."""

from pathlib import Path
import csv
import gzip
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from threadpoolctl import threadpool_limits
from scripts.run_baselines import POLICIES, summarize
from twenty_bits.baselines import play
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.prompts import get_tokenizer
from twenty_bits.provenance import check_baseline_provenance
from twenty_bits.worlds import ROOT


def main():
    destination = ROOT / "results/baselines/frozen"
    destination.mkdir(exist_ok=True)
    check_baseline_provenance(destination, "paid-v1", 200)
    summaries = []
    with threadpool_limits(limits=1):
        for c in frozen_manifest()["cells"]:
            path = destination / c["file"]
            if path.exists():
                rows = [
                    json.loads(line)
                    for line in gzip.decompress(path.read_bytes()).decode().splitlines()
                ]
            else:
                rows = []
                for record in frozen_games(c["domain"], c["n"], c["noise"]):
                    for policy in POLICIES:
                        rows.append(play(record, policy, tokenizer=get_tokenizer()))
                path.write_bytes(
                    gzip.compress(
                        "".join(
                            json.dumps(row, separators=(",", ":")) + "\n"
                            for row in rows
                        ).encode(),
                        mtime=0,
                    )
                )
            for policy in POLICIES:
                summaries.append(
                    {k: c[k] for k in ["domain", "n", "noise"]}
                    | {"policy": policy}
                    | summarize([r for r in rows if r["policy"] == policy])
                )
            print(c["domain"], c["n"], c["noise"], flush=True)
    (destination / "summary.json").write_text(
        json.dumps(summaries, indent=2, allow_nan=False) + "\n"
    )
    scalar = [
        {k: v for k, v in row.items() if not k.endswith("_ci95")} for row in summaries
    ]
    with (destination / "summary.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(scalar[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(scalar)


if __name__ == "__main__":
    main()
