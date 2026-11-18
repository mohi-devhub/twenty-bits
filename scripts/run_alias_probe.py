"""Run only the approved $0.25 attribute-alias probe. No training occurs here."""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_learnability_probe import main
from twenty_bits.worlds import ROOT


if __name__ == "__main__":
    asyncio.run(
        main(
            config_path=ROOT / "experiments/alias_probe.json",
            proof_path=ROOT / "research/alias_probe_rendering.json",
            games_path=ROOT / "experiments/learnability_probe_games.json",
            results_path=ROOT / "results/alias_probe",
            approved_run_cap="0.250000",
        )
    )
