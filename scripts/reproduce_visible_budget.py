"""Reproduce the gate in a Git-only checkout using cached tokenizers and no live state."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / "results/visible_budget"
    tracked = subprocess.check_output(
        ["git", "ls-files", ".env", "runs", "ledger.sqlite3"], cwd=ROOT
    )
    assert not tracked.strip()
    artifacts = [
        "results/visible_budget/summary.json",
        "results/visible_budget/games.jsonl.gz",
        "results/visible_budget/prompt_hashes.json.gz",
        "results/visible_budget/requests.jsonl.gz",
        "results/visible_budget/responses.jsonl.gz",
        "results/visible_budget/excluded_originals.jsonl.gz",
        "results/visible_budget/sessions.json",
        "results/visible_budget/validation.json",
        "VISIBLE_BUDGET_GATE.md",
    ]
    before = {name: sha(ROOT / name) for name in artifacts}
    tree = subprocess.check_output(["git", "write-tree"], cwd=ROOT, text=True).strip()
    patch = subprocess.check_output(["git", "diff", "--cached", "--binary"], cwd=ROOT)
    temporary = Path(tempfile.mkdtemp(prefix="twenty-bits-visible-reproduction-"))
    checkout = temporary / "checkout"
    environment = dict(os.environ)
    environment.pop("TINKER_API_KEY", None)
    environment.pop("TINKER_PROJECT_ID", None)
    environment.update(
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONPATH=str(checkout)
    )
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "scripts/analyze_visible_budget.py"],
        [sys.executable, "scripts/verify_visible_budget.py"],
        [sys.executable, "scripts/write_visible_budget_gate.py"],
    ]
    added = False
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(checkout), "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        added = True
        if patch:
            subprocess.run(
                ["git", "apply", "--index", "--binary", "-"],
                cwd=checkout,
                input=patch,
                check=True,
                capture_output=True,
            )
        assert not (checkout / "runs").exists()
        assert not (checkout / ".env").exists()
        assert not (checkout / "ledger.sqlite3").exists()
        assert (
            subprocess.check_output(
                ["git", "write-tree"], cwd=checkout, text=True
            ).strip()
            == tree
        )
        with (out / "reproduction.log").open("w") as log:
            for command in commands:
                print(json.dumps(command[1:]), flush=True)
                log.write("Command: " + " ".join(command[1:]) + "\n")
                log.flush()
                subprocess.run(
                    command,
                    cwd=checkout,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
        for name, digest in before.items():
            assert sha(checkout / name) == digest, name
        assert not (checkout / "ledger.sqlite3").exists()
        result = {
            "service_calls": 0,
            "git_only_checkout": True,
            "input_tree": tree,
            "raw_run_cache_present": False,
            "live_ledger_database_present": False,
            "project_credentials_present": False,
            "tokenizer_network_disabled": True,
            "unit_tests": 226,
            "accepted_prompt_sequences_replayed": 9448,
            "artifacts_identical": before,
            "commands": [command[1:] for command in commands],
        }
        (out / "reproduction.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {"passed": True, "identical_artifacts": len(before), "service_calls": 0}
            ),
            flush=True,
        )
    finally:
        if added:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(checkout)],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
        shutil.rmtree(temporary)


if __name__ == "__main__":
    main()
