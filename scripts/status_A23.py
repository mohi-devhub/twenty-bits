"""Read local A23 progress and budget without contacting Tinker."""

import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger


ROOT=Path(__file__).resolve().parent.parent


def main():
    curve=ROOT/"results/main_A23/learning_curve.json"
    updates=json.loads(curve.read_text())["updates"] if curve.exists() else []
    status={"updates_completed":len(updates)}
    if updates:
        status["latest_group"]={k:updates[-1][k] for k in ("update","n","wins","mean_reward","eig_per_question","questions_per_win")}
    checks=[]
    for step in (0,4,8,12,16,20,24,28,30):
        p=ROOT/f"results/main_A23/development-{step:02d}.json"
        if p.exists():
            d=json.loads(p.read_text())
            checks.append({"update":step,"wins":d["wins"],"eig":d["eig_per_question"]})
    status["development"]=checks
    status["saved_games"]={run:sum(1 for _ in (ROOT/"runs"/run/"games").glob("*.json")) for run in ("main-U-A23-v1","A23-suffix-v1","A23-hard-v1")}
    ledger=Ledger(ROOT/"ledger.json").status()
    status["budget"]={k:v for k,v in ledger.items() if k!="entries"}
    status["stage_complete"]=(ROOT/"results/main_A23/completion.json").exists()
    print(json.dumps(status,separators=(",",":")))


if __name__=="__main__":main()
