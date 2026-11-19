"""Guarded, resumable evaluation of fixed policies with a visible counter."""

import asyncio
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx
from tinker import types
from tinker_cookbook.rl.rollouts import do_single_rollout

from twenty_bits.guess_metrics import guess_state
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.recovery import RecoveringTransport
from twenty_bits.replacement_registry import refresh_legacy_ids
from twenty_bits.rl_pilot import SamplingScope, pack_trajectory
from twenty_bits.tinker_transport import NetworkInterruption, save_json
from twenty_bits.visible_budget import visible_budget_messages
from twenty_bits.worlds import ROOT
import gzip


def check_frozen():
    proof = json.loads((ROOT / "research/visible_budget_preflight.json").read_text())
    for path, digest in proof["immutable_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Follow-up input changed: {path}; no SDK access.")
    config = json.loads((ROOT / "experiments/visible_budget.json").read_text())
    approval = json.loads((ROOT / "research/visible_budget_approval.json").read_text())
    price = json.loads((ROOT / "research/visible_budget_forecast.json").read_text())
    if not approval["dispatch_authorized_now"] or not price["fits"]:
        raise RuntimeError(
            "The visible-budget follow-up is not authorized to dispatch."
        )
    if (
        config["training_authorized"]
        or config["rl_training_authorized"]
        or not config["eval_only"]
        or config["run_cap_usd"] != "8.000000"
    ):
        raise RuntimeError(
            "Follow-up must remain eval-only with the approved $8 ceiling."
        )
    return config, proof


async def load_policy(t, policy, sequence):
    key = str(policy["snapshot_key"])
    if key not in t.state.get("snapshots", {}):
        result = await t.free(
            f"create visible-budget {policy['name']} native sampler",
            lambda: t.client.service.create_sampling_session(
                request=types.CreateSamplingSessionRequest(
                    session_id=t.state["session_id"],
                    sampling_session_seq_id=sequence,
                    base_model=t.config["primary_model"],
                    model_path=policy["model_path"],
                )
            ),
        )
        t.state.setdefault("snapshots", {})[key] = {
            "id": result["sampling_session_id"],
            "next_seq": 0,
            "policy_step": policy["training_updates"],
            "native_checkpoint_path": policy["model_path"],
            "policy": policy["name"],
        }
        save_json(t.state_path, t.state)
    saved = t.state["snapshots"][key]
    if (
        saved["native_checkpoint_path"] != policy["model_path"]
        or saved["policy"] != policy["name"]
    ):
        raise RuntimeError("Saved native sampler belongs to a different fixed policy.")
    t.active_step = policy["snapshot_key"]


async def run_once():
    out = ROOT / "results/visible_budget"
    if (out / "completion.json").exists():
        print("Visible-budget follow-up complete. No service calls.", flush=True)
        return
    config, proof = check_frozen()
    records = json.loads(
        gzip.decompress(
            (ROOT / "experiments/visible_budget_games.json.gz").read_bytes()
        )
    )
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        registry_path = ROOT / "research/visible_budget_replacements.json"
        refresh_legacy_ids(registry_path)
        t = RecoveringTransport(
            config,
            directory,
            usage_path=out / "usage.jsonl",
            run_cap_usd=config["run_cap_usd"],
            registry_path=registry_path,
        )
        stop_event = asyncio.Event()
        stopped = False
        heartbeat = None
        tasks = []
        failure = None
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stopped
            stopped = True
            t.failed = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop)
        semaphore = asyncio.Semaphore(config["concurrent_games"])

        async def play(record, policy):
            scope = f"visible-budget/{policy['name']}/"
            path = (
                directory
                / "games"
                / (
                    hashlib.sha256((scope + record["id"]).encode()).hexdigest()
                    + ".json"
                )
            )
            if path.exists():
                return json.loads(path.read_text())
            async with semaphore:
                if t.failed or stopped:
                    raise RuntimeError(
                        "New follow-up submissions stopped; draining futures."
                    )
                if heartbeat.done():
                    heartbeat.result()
                env = TableEnv(
                    record,
                    config["primary_model"],
                    config,
                    message_builder=visible_budget_messages,
                )
                trajectory = await do_single_rollout(
                    GuardedCompleter(SamplingScope(t, scope), env), env
                )
                result = env.result()
                if (
                    not env.game.done
                    or abs(
                        sum(x.reward for x in trajectory.transitions) - result["reward"]
                    )
                    > 1e-10
                ):
                    raise RuntimeError("Follow-up cookbook return mismatch.")
                result.update(
                    policy=policy["name"],
                    kind="visible_budget",
                    update=policy["training_updates"],
                    policy_step=policy["training_updates"],
                    snapshot_key=policy["snapshot_key"],
                    is_primary_result=False,
                    eval_only=True,
                    scope=scope,
                    prompt_version=config["prompt_version"],
                    sampling_seed_namespace=config["sampling_seed_namespace"],
                    guess_state=guess_state(result, record),
                    trajectory=pack_trajectory(trajectory),
                )
                save_json(path, result)
                print(
                    json.dumps(
                        {
                            "policy": policy["name"],
                            "game": record["id"],
                            "won": result["won"],
                            "questions": result["questions"],
                            "eig": result["eig_per_question"],
                            "run_budget": t.run_status(),
                        }
                    ),
                    flush=True,
                )
                return result

        try:
            await t.open(recover_pending=True)
            heartbeat = asyncio.create_task(t.heartbeat(stop_event))
            results = []
            for sequence, policy in enumerate(config["policies"]):
                await load_policy(t, policy, sequence)
                tasks = [
                    asyncio.create_task(play(record, policy)) for record in records
                ]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                errors = [r for r in outcomes if isinstance(r, BaseException)]
                if errors:
                    t.failed = True
                    raise next(
                        (r for r in errors if isinstance(r, NetworkInterruption)),
                        errors[0],
                    )
                results.extend(outcomes)
                save_json(
                    out / f"{policy['name']}_collected.json",
                    {
                        "games": len(outcomes),
                        "wins": sum(g["won"] for g in outcomes),
                        "policy": policy,
                        "run_budget": t.run_status(),
                    },
                )
            await t.finish()
            save_json(
                out / "completion.json",
                {
                    "eval_only": True,
                    "is_primary_result": False,
                    "games": len(results),
                    "config_sha256": proof["immutable_sha256"][
                        "experiments/visible_budget.json"
                    ],
                    "policies": config["policies"],
                    "A11": config["skipped_policies"]["A11"],
                    "run_budget": t.run_status(),
                    "finished_session": True,
                },
            )
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


async def main():
    while True:
        try:
            return await run_once()
        except (NetworkInterruption, httpx.TransportError):
            print(
                "Network interrupted: HTTP drained; collect saved futures before new submissions.",
                flush=True,
            )
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
