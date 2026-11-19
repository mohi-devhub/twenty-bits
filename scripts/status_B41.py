"""Read B41 progress and current live budget without making service calls."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Read the explicit JSON audit export; it may be stale during a run.",
    )
    args = parser.parse_args()
    out = ROOT / "results/main_B41"
    curve = out / "learning_curve.json"
    updates = json.loads(curve.read_text())["updates"] if curve.exists() else []
    result = {
        "completed_updates": len(updates),
        "endpoint_complete": (out / "completion.json").exists(),
        "budget": (
            {
                k: v
                for k, v in Ledger.snapshot_status(ROOT / "ledger.json").items()
                if k != "entries"
            }
            if args.snapshot
            else Ledger(ROOT / "ledger.json").summary()
        ),
        "budget_source": "JSON audit export" if args.snapshot else "live SQLite",
    }
    if updates:
        last = updates[-1]
        result["latest_update"] = {
            k: last.get(k)
            for k in [
                "update",
                "n",
                "wins",
                "win_rate",
                "mean_reward",
                "eig_per_question",
                "questions_per_win",
                "output_tokens_per_game",
                "nonzero_group_fraction",
            ]
        }
    dev = sorted(out.glob("development-*.json"))
    if dev:
        d = json.loads(dev[-1].read_text())
        result["latest_development"] = {
            k: d.get(k)
            for k in [
                "policy_step",
                "wins",
                "win_rate",
                "eig_per_question",
                "mean_reward",
            ]
        }
    games = ROOT / "runs/main-U-B41-v1/games"
    if games.exists():
        result["saved_games"] = sum(1 for _ in games.glob("*.json"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
