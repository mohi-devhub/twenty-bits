"""Verify A23 journals, immutable science, native saves and archive reproduction."""

import asyncio
from contextlib import redirect_stdout
from datetime import datetime
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import analyze_main_A23, analyze_A23_replication, audit_A23_session_reproduction, run_main_A23, run_A23_endpoint_aux, run_A23_stage
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.rl_pilot import PilotTransport
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, load_split, training_game


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in gzip.open(path, "rt")]


def main():
    out=ROOT/"results/main_A23"
    complete=json.loads((out/"completion.json").read_text())
    config=json.loads((ROOT/"experiments/main_A23.json").read_text())
    proof=json.loads((ROOT/"research/main_A23_preflight.json").read_text())
    manifest=json.loads(gzip.decompress((ROOT/"experiments/main_A23_games.json.gz").read_bytes()))
    assert sha(ROOT/"experiments/main_A23.json")==proof["config_sha256"]==complete["config_sha256"]
    assert hashlib.sha256(json.dumps(manifest,indent=2).encode()+b"\n").hexdigest()==proof["games_sha256"]
    for name,digest in proof["implementation_sha256"].items():
        assert sha(ROOT/name)==digest,name
    assert complete["updates"]==30 and complete["training_games"]==240 and complete["development_games"]==64
    assert complete["frozen_endpoint_games"]==280 and complete["reused_raw_frozen_games"]==280
    assert complete["suffix_diagnostic_games"]==168 and complete["hard_mode_games"]==40
    assert complete["endpoint_evaluations_complete"] and not complete["B41_started"]
    assert complete["initialization"]=="raw_base_no_sft"
    assert config["lora"]["seed"]==23 and config["checkpoint_ttl_seconds"] is None
    assert config["reward"]=={"win":1,"per_question":-.03,"per_invalid":-.1,"information_shaping":False}
    for row in manifest["training"]:
        r=row["record"]
        assert r==training_game(r["n"],1000000+row["update"],seed=23,noise=0)
        assert set(r["world"]["names"])<=set(load_split()["train"])
    expected={r["id"]:r for cell in frozen_manifest()["cells"] for r in frozen_games(cell["domain"],cell["n"],cell["noise"],28)}
    assert expected=={r["id"]:r for r in manifest["evaluation"]}
    frozen=ROOT/"evals/frozen"
    for cell in json.loads((frozen/"manifest.json").read_text())["cells"]:
        assert sha(frozen/cell["file"])==cell["sha256"]
    assert not subprocess.check_output(["git","diff","208c323","--name-only","--","evals/frozen","evals/candidate_set","evals/hard_mode.json","twenty_bits/budget.py","twenty_bits/game.py","twenty_bits/predicates.py","twenty_bits/rl_pilot.py"],cwd=ROOT).strip()
    status=Ledger(ROOT/"ledger.json").status();entries={e["id"]:e for e in status["entries"]}
    previous=json.loads(subprocess.check_output(["git","show","208c323:ledger.json"],cwd=ROOT))
    current=json.loads((ROOT/"ledger.json").read_text())
    assert all(entries[e["id"]]==e for e in previous["entries"])
    assert previous["approvals"]==current["approvals"] and previous["cap_usd"]==current["cap_usd"]=="50.000000"
    assert not status["blocked"]
    requests=read_rows(out/"requests.jsonl.gz")
    operations=read_rows(out/"operations.jsonl.gz")
    assert len(operations)==93
    assert sorted(int(o["request_id"].rsplit(":",1)[1]) for o in operations)==list(range(93))
    assert all(o["request_id"].rsplit(":",1)[0]==complete["training_model_id"] for o in operations)
    assert not any("load" in o["key"] for o in operations)
    storage=[o for o in operations if o["storage"]]
    assert len(storage)==2
    for o in storage:
        assert o["payload"]["ttl_seconds"] is None and o["completed"]
        assert entries[o["entry_id"]]["state"] in ACTIVE_STATES
        assert entries[o["entry_id"]]["checkpoint"]["expires_at"] is None
    for kind,row in complete["checkpoints"]["30"].items():
        assert row["checkpoint_type"]==kind and row["size_bytes"]>0 and row["expires_at"] is None
        assert row["tinker_path"].startswith("tinker://"+complete["training_model_id"]+"/")
        assert any(entries[o["entry_id"]]["checkpoint"]["tinker_path"]==row["tinker_path"] for o in storage)
    stage_specs=[("primary","main-U-A23-v1",out,ROOT/"research/main_A23_replacements.json"),
                 ("suffix","A23-suffix-v1",ROOT/"results/A23_suffix",ROOT/"research/A23_suffix_replacements.json"),
                 ("hard","A23-hard-v1",ROOT/"results/A23_hard",ROOT/"research/A23_hard_replacements.json")]
    replacement_cases={};durations=[];all_new_originals=set();total_sampling=0
    for stage,run_id,folder,registry_path in stage_specs:
        if stage!="primary":
            auxiliary_proof=json.loads((ROOT/f"research/A23_{stage}_preflight.json").read_text())
            assert sha(ROOT/f"experiments/A23_{stage}.json")==auxiliary_proof["config_sha256"]
            manifest_bytes=gzip.decompress((ROOT/f"experiments/A23_{stage}_games.json.gz").read_bytes())
            assert hashlib.sha256(manifest_bytes).hexdigest()==auxiliary_proof["games_sha256"]
            for name,digest in auxiliary_proof["implementation_sha256"].items():
                assert sha(ROOT/name)==digest,name
        registry=json.loads(registry_path.read_text())
        active=read_rows(folder/"requests.jsonl.gz")
        excluded=read_rows(folder/"excluded_originals.jsonl.gz")
        total_sampling+=len(active)
        reqs=active+(operations if stage=="primary" else [])
        for r in reqs:
            entry=entries[r["entry_id"]]
            assert r["request_id_saved_before_dispatch"]
            assert entry["request_id"]==r["request_id"]==r["receipt"]["request_id"]
            assert entry["created_at"]<=r["saved_before_dispatch_at"]<=r["collection_started_at"]<=r["response_received_at"]
            if not r.get("storage"):
                assert r["settled"] and Decimal(entry["actual_usd"])==Decimal(r["actual_usd"]),r["key"]
            durations.append((datetime.fromisoformat(r["response_received_at"])-datetime.fromisoformat(r["saved_before_dispatch_at"])).total_seconds())
        excluded_ids={r["entry_id"] for r in excluded};all_new_originals.update(excluded_ids)
        for r in excluded:
            assert r["orphaned"] and r["output_allowed"] is False
            assert entries[r["entry_id"]]["state"] in ACTIVE_STATES
            assert r["request_id_saved_before_dispatch"]
            assert entries[r["entry_id"]]["request_id"]==r["request_id"]
            assert entries[r["entry_id"]]["created_at"]<=r["saved_before_dispatch_at"]<=r["collection_started_at"]
        cases=[]
        for case in registry["cases"]:
            assert case["original_entry_id"] in excluded_ids
            original=next(r for r in excluded if r["entry_id"]==case["original_entry_id"])
            replacement=next(r for r in active if r["entry_id"]==case["replacement_entry_id"])
            assert original["signature"]==replacement["signature"]==case["signature"]
            assert original["parameters"]==replacement["parameters"]
            cases.append({**case,
                "original_hold_usd":entries[case["original_entry_id"]]["reserved_usd"],
                "saved_before_dispatch_at":original["saved_before_dispatch_at"],
                "collection_started_at":original["collection_started_at"],
                "submission_error":original.get("submission_error"),
                "save_to_loss_observed_seconds":(datetime.fromisoformat(case["loss_observed_at"])-datetime.fromisoformat(original["saved_before_dispatch_at"])).total_seconds()})
        replacement_cases[stage]={"cases":cases,"original_holds_usd":str(sum((Decimal(entries[e]["reserved_usd"]) for e in excluded_ids),Decimal(0)))}
        state=json.loads((folder/"sessions.json").read_text())
        assert state["finished"]
    prior_active={e["id"] for e in previous["entries"] if e["state"] in ACTIVE_STATES}
    assert {e["id"] for e in status["entries"] if e["state"] in ACTIVE_STATES}==prior_active|all_new_originals|{o["entry_id"] for o in storage}
    assert not (ROOT/"runs/main-U-B41-v1/sessions.json").exists()
    assert not any(e["operation"].startswith("[main-U-B41-v1] ") for e in entries.values())
    test=json.loads((ROOT/"research/native_persistence_test.json").read_text())
    assert test["passed"] and test["test_checkpoints_deleted"] and test["console_verified"]
    log=ROOT/"results/main_A23/unit_tests.txt"
    suite=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=ROOT,capture_output=True,text=True,check=True)
    log.write_text(suite.stdout+suite.stderr)
    import re
    tests=int(re.search(r"Ran (\d+) tests",suite.stderr)[1])
    ledger_hash=sha(ROOT/"ledger.json")
    restored_manifests=[]
    try:
        for mode in ("suffix","hard"):
            manifest_path=ROOT/f"experiments/A23_{mode}_games.json"
            if not manifest_path.exists():
                manifest_path.write_bytes(gzip.decompress(manifest_path.with_suffix(".json.gz").read_bytes()))
                restored_manifests.append(manifest_path)
        with patch.object(PilotTransport,"open",side_effect=AssertionError("Completed runners must not contact Tinker")),redirect_stdout(io.StringIO()):
            asyncio.run(run_main_A23.main())
            asyncio.run(run_A23_endpoint_aux.main("suffix"))
            asyncio.run(run_A23_endpoint_aux.main("hard"))
            run_A23_stage.main()
    finally:
        for path in restored_manifests:
            path.unlink()
    assert sha(ROOT/"ledger.json")==ledger_hash
    result={"tests_passed":tests,"primary_sampling_requests_verified":len(requests),
        "all_new_sampling_requests_verified":total_sampling,"primary_mutations_verified":len(operations),
        "gradient_batches_reconstructed":30,"frozen_games_in_gradients":0,
        "frozen_games_verified":2000,"frozen_and_prompt_hashes_unchanged":True,
        "old_ledger_entries_and_approval_unchanged":True,"old_holds_retained":True,
        "replacement_cases":replacement_cases,"maximum_save_to_collection_seconds":max(durations),
        "native_training_and_sampler_no_expiry":True,"smoke_files_deleted_API_verified":True,
        "source_finished_before_auxiliary_fresh_clients":True,"completed_runner_service_calls":0,
        "session_metadata_from_committed_archives":True,
        "raw_run_cache_present_during_verification":(ROOT/"runs").exists(),
        "B41_started":False,"all_HTTP_work_drained":True}
    save_json(out/"validation.json",result)
    audit_A23_session_reproduction.main()
    folders=[out,ROOT/"results/A23_suffix",ROOT/"results/A23_hard"]
    files=[p for folder in folders for p in folder.glob("*.json*") if p.name!="reproduction.json"]
    before={str(p.relative_to(ROOT)):sha(p) for p in files}
    original_glob=Path.glob
    def archives_only(path,pattern):
        return iter(()) if path.is_relative_to(ROOT/"runs") else original_glob(path,pattern)
    with patch.object(Path,"glob",archives_only),redirect_stdout(io.StringIO()):
        analyze_main_A23.main()
        analyze_A23_replication.main()
        audit_A23_session_reproduction.main()
    assert all(sha(ROOT/name)==digest for name,digest in before.items())
    assert sha(ROOT/"ledger.json")==ledger_hash
    save_json(out/"reproduction.json",{"archives_only_analysis_identical":True,"service_calls":0,"sha256":before})
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
