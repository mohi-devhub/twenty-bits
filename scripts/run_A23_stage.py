"""Run A23 and every approved endpoint evaluation, then stop before B41."""

import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def main():
    persistence = ROOT / "research/native_persistence_test.json"
    if not persistence.exists() or not json.loads(persistence.read_text()).get("passed"):
        print("Native persistence requires console verification and test cleanup. No service calls.")
        return
    complete = ROOT / "results/main_A23/completion.json"
    if complete.exists():
        print("A23 gate reached; B41 requires the user's decision. No service calls.")
        return
    commands = [
        ["scripts/run_main_A23.py"],
        ["scripts/run_A23_endpoint_aux.py", "--mode", "suffix"],
        ["scripts/run_A23_endpoint_aux.py", "--mode", "hard"],
    ]
    for args in commands:
        subprocess.run([sys.executable, *args], cwd=ROOT, check=True)
    primary = json.loads((ROOT / "results/main_A23/primary_completion.json").read_text())
    suffix = json.loads((ROOT / "results/A23_suffix/completion.json").read_text())
    hard = json.loads((ROOT / "results/A23_hard/completion.json").read_text())
    assert primary["updates"] == 30 and suffix["games"] == 168 and hard["games"] == 40
    status = Ledger(ROOT / "ledger.json").status()
    save_json(complete, {**primary, "suffix_diagnostic_games":168,
        "hard_mode_games":40, "endpoint_evaluations_complete":True,
        "A11_suffix_and_hard_mode":"not run: A11 checkpoint wasn't persisted, external uploads unavailable",
        "B41_started":False, "next_gate":"Stop before B41; report A11 versus A23.",
        "project_budget":{k:v for k,v in status.items() if k!="entries"}})
    print("A23 training and endpoint evaluations complete. Stop before B41.", flush=True)


if __name__ == "__main__":
    main()
