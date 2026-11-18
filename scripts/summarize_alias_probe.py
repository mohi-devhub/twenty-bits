"""Audit the alias probe and apply its declared conditional-SFT decision rule."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.summarize_learnability_probe import main
from twenty_bits.worlds import ROOT


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial", action="store_true")
    main(
        parser.parse_args().partial,
        config_path=ROOT / "experiments/alias_probe.json",
        output_path=ROOT / "results/alias_probe",
    )
