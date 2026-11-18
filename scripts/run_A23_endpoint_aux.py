"""Immediate A23 endpoint diagnostics; primary training never imports this file."""

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx
import tinker
from tinker import types
from tinker_cookbook.rl.rollouts import do_single_rollout

from scripts.run_main_seed import metrics
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.guess_metrics import guess_state
from twenty_bits.learnability import probe_messages
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.recovery import RecoveringTransport
from twenty_bits.replacement_registry import refresh_legacy_ids
from twenty_bits.rl_pilot import SamplingScope, pack_trajectory
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame
from twenty_bits.tinker_transport import NetworkInterruption, save_json
from twenty_bits.worlds import ROOT


async def load_policy(t, step, model_path):
    if str(step) not in t.state.get("snapshots", {}):
        seq = 0 if step == 0 else 1
        result = await t.free("create fresh native endpoint sampler" if model_path else "create raw hard-mode sampler",
            lambda: t.client.service.create_sampling_session(request=types.CreateSamplingSessionRequest(
                session_id=t.state["session_id"], sampling_session_seq_id=seq,
                base_model=t.config["primary_model"], model_path=model_path)))
        t.state.setdefault("snapshots", {})[str(step)] = {
            "id": result["sampling_session_id"], "next_seq": 0,
            "policy_step": step, "native_checkpoint_path": model_path}
        save_json(t.state_path, t.state)
    t.active_step = step


async def run_once(mode):
    config_path = ROOT / f"experiments/A23_{mode}.json"
    config = json.loads(config_path.read_text())
    proof = json.loads((ROOT / f"research/A23_{mode}_preflight.json").read_text())
    if hashlib.sha256(config_path.read_bytes()).hexdigest() != proof["config_sha256"]:
        raise RuntimeError("Endpoint auxiliary settings changed.")
    for name, digest in proof["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Endpoint auxiliary implementation changed.")
    primary = json.loads((ROOT / "results/main_A23/primary_completion.json").read_text())
    checkpoint = primary["checkpoints"]["30"]["sampler"]["tinker_path"]
    if primary["checkpoints"]["30"]["sampler"]["expires_at"] is not None:
        raise RuntimeError("A23 auxiliary work requires a persistent native endpoint.")
    records = json.loads((ROOT / f"experiments/A23_{mode}_games.json").read_bytes())
    if hashlib.sha256((ROOT / f"experiments/A23_{mode}_games.json").read_bytes()).hexdigest() != proof["games_sha256"]:
        raise RuntimeError("Endpoint auxiliary frozen cases changed.")
    out = ROOT / f"results/A23_{mode}"
    complete = out / "completion.json"
    if complete.exists():
        print(f"A23 {mode} complete. No service calls.", flush=True)
        return
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        registry_path = ROOT / f"research/A23_{mode}_replacements.json"
        refresh_legacy_ids(registry_path)
        t = RecoveringTransport(config, directory, usage_path=out / "usage.jsonl",
            run_cap_usd=config["run_cap_usd"],
            registry_path=registry_path)
        stop_event = asyncio.Event()
        heartbeat = None
        tasks = []
        stopped = False
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stopped
            stopped = True
            t.failed = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop)
        semaphore = asyncio.Semaphore(int(os.environ.get("TWENTY_BITS_CONCURRENT_GAMES", "16")))

        async def play(record, policy):
            scope = f"{mode}/{policy}/"
            path = directory / "games" / (hashlib.sha256((scope + record["id"]).encode()).hexdigest() + ".json")
            if path.exists():
                return json.loads(path.read_text())
            async with semaphore:
                if t.failed or stopped:
                    raise RuntimeError("Auxiliary submissions stopped while futures drain.")
                if heartbeat.done():
                    heartbeat.result()
                builder = candidate_messages if mode == "suffix" else probe_messages
                env = TableEnv(record, config["primary_model"], config, message_builder=builder)
                if mode == "suffix":
                    env.game = SuffixDiagnosticGame(record)
                trajectory = await do_single_rollout(GuardedCompleter(SamplingScope(t, scope), env), env)
                result = env.result()
                if not env.game.done or abs(sum(x.reward for x in trajectory.transitions) - result["reward"]) > 1e-10:
                    raise RuntimeError("Auxiliary cookbook return mismatch.")
                result.update(policy=policy, kind=mode, update=t.active_step,
                    is_primary_result=False, scope=scope,
                    diagnostic_only=(mode == "suffix"),
                    sampling_seed_namespace=config["sampling_seed_namespace"],
                    guess_state=guess_state(result, record), trajectory=pack_trajectory(trajectory))
                save_json(path, result)
                print(json.dumps({"mode": mode, "policy": policy, "game": record["id"],
                                  "won": result["won"], "eig": result["eig_per_question"],
                                  "mapped_identifiers": result.get("mapped_identifiers", 0)}), flush=True)
                return result

        failure = None
        try:
            await t.open(recover_pending=True)
            heartbeat = asyncio.create_task(t.heartbeat(stop_event))
            policies = [(0, "raw_base", None), (30, "A23_endpoint", checkpoint)] if mode == "hard" else [(30, "A23_suffix_DIAGNOSTIC_ONLY", checkpoint)]
            results = []
            for step, policy, path in policies:
                await load_policy(t, step, path)
                tasks = [asyncio.create_task(play(r, policy)) for r in records]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                errors = [r for r in outcomes if isinstance(r, BaseException)]
                if errors:
                    t.failed = True
                    raise next((r for r in errors if isinstance(r, NetworkInterruption)), errors[0])
                results.extend(outcomes)
            await t.finish()
            save_json(complete, {"mode": mode, "games": len(results), "diagnostic_only": mode == "suffix",
                "native_endpoint_path": checkpoint, "config_sha256": proof["config_sha256"],
                "run_budget": t.run_status(), "metrics": {policy: metrics([g for g in results if g["policy"] == policy]) for _, policy, _ in policies}})
        except Exception as exc:
            failure = exc
        finally:
            t.failed = True
            await asyncio.gather(*tasks, return_exceptions=True)
            stop_event.set()
            if heartbeat:
                await asyncio.gather(heartbeat, return_exceptions=True)
            await t.close()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
        if failure:
            raise failure


async def main(mode):
    while True:
        try:
            return await run_once(mode)
        except (NetworkInterruption, httpx.TransportError):
            print("Network interrupted; drained HTTP, collecting saved futures before new work.", flush=True)
            await asyncio.sleep(1)
        except tinker.APIStatusError as exc:
            if exc.status_code == 429 or exc.status_code >= 500:
                await asyncio.sleep(1)
                continue
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("suffix", "hard"), required=True)
    asyncio.run(main(parser.parse_args().mode))
