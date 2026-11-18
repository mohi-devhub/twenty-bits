"""Audit the completed format SFT and qualification, with no service calls."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.summarize_learnability_probe import main
from twenty_bits.worlds import ROOT


if __name__ == "__main__":
    main(
        config_path=ROOT / "experiments/format_sft.json",
        games_path=ROOT / "experiments/format_qualification_games.json",
        output_path=ROOT / "results/format_sft",
    )
