"""Run only the approved B41 seed, export its ledger, then stop at its gate."""

import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def main():
    complete = ROOT / "results/main_B41/completion.json"
    if complete.exists() and json.loads(complete.read_text()).get(
        "ledger_export_complete"
    ):
        print("B41 gate reached. No service calls.", flush=True)
        return
    subprocess.run([sys.executable, "scripts/run_main_B41.py"], cwd=ROOT, check=True)
    result = json.loads(complete.read_text())
    assert result["updates"] == 30 and result["frozen_endpoint_games"] == 280
    ledger = Ledger(ROOT / "ledger.json")
    ledger.export_snapshot()
    result.update(
        project_budget=ledger.summary(),
        ledger_export_complete=True,
        all_HTTP_work_drained=True,
        next_gate="Stop at MAIN_B41_GATE.md. No further paid work is authorized.",
    )
    save_json(complete, result)
    plan = json.loads((ROOT / "research/active_plan.json").read_text())
    plan.update(
        status="B41 complete; stopped at the final main-seed gate.",
        active_stage="B41_gate",
        dispatch_authorized_now=False,
        current_gate="MAIN_B41_GATE.md",
        training_updates_completed=30,
        endpoint_games_saved=280,
        project_usage_at_recording=ledger.summary(),
        next_action="Finish offline B41 analysis, report all main seeds, commit and wait.",
    )
    save_json(ROOT / "research/active_plan.json", plan)
    print("B41 training and scheduled endpoint complete. Stop at its gate.", flush=True)


if __name__ == "__main__":
    main()
