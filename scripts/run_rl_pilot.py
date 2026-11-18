"""Run the approved A pilot, including its development checks, then stop."""

import asyncio
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker_cookbook.rl.rollouts import do_single_rollout
from scripts.run_format_sft import download_export
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.rl_pilot import (
    GuardedRL,
    PilotTransport,
    SamplingScope,
    group_data,
    pack_trajectory,
    unpack_trajectory,
)
from twenty_bits.tinker_transport import NetworkInterruption, save_json
from twenty_bits.worlds import ROOT, training_game


def game_metrics(games):
    questions = sum(g["questions"] for g in games)
    winners = [g for g in games if g["won"]]
    turns = [t for g in games for t in g["turns"]]
    return {
        "games": len(games),
        "mean_reward": float(np.mean([g["reward"] for g in games])),
        "wins": len(winners),
        "win_rate": len(winners) / len(games),
        "questions_per_win": float(np.mean([g["questions"] for g in winners]))
        if winners
        else None,
        "eig_per_question": sum(sum(g["question_eigs"]) for g in games) / questions
        if questions
        else None,
        "enumeration_rate": sum(g["enumeration_count"] for g in games) / questions
        if questions
        else None,
        "single_item_enumeration_rate": sum(
            g["singleton_enumeration_questions"] for g in games
        )
        / questions
        if questions
        else None,
        "name_list_rate": sum(
            t["is_question"] and not t["invalid"] and t["named_items"] >= 2
            for t in turns
        )
        / questions
        if questions
        else None,
        "large_name_list_rate": sum(g["large_name_list_questions"] for g in games)
        / questions
        if questions
        else None,
        "invalid_question_rate": sum(g["invalid_count"] for g in games) / questions
        if questions
        else None,
        "output_tokens_per_game": sum(g["output_tokens"] for g in games) / len(games),
        "reasoning_tokens_per_game": sum(g["reasoning_tokens"] for g in games)
        / len(games),
        "questions": questions,
        "post_budget_non_guesses": sum(bool(t.get("forced_end")) for t in turns),
        "truncated_turns": sum(t["truncated"] for t in turns),
    }


async def run_once():
    path = ROOT / "experiments/pilot_A.json"
    config = json.loads(path.read_text())
    proof = json.loads((ROOT / "research/pilot_A_preflight.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != proof["config_sha256"]:
        raise RuntimeError("The approved pilot settings changed.")
    complete = ROOT / "results/pilot_A/completion.json"
    if complete.exists():
        if json.loads(complete.read_text())["config_sha256"] != proof["config_sha256"]:
            raise RuntimeError("Completed pilot used different settings.")
        print("The approved pilot is complete. No service calls.", flush=True)
        return
    for name, digest in proof["implementation_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("The frozen RL implementation changed.")
    manifest_path = ROOT / "experiments/pilot_A_games.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != proof["games_sha256"]:
        raise RuntimeError("The fixed pilot games changed.")
    manifest = json.loads(manifest_path.read_text())
    for row in manifest["training"]:
        r = row["record"]
        if r != training_game(r["n"], 800000 + row["update"], seed=11, noise=0):
            raise RuntimeError(
                "Pilot training must use its fixed training-pool factory."
            )
    if (
        not config["rl_training_authorized"]
        or config["initial_policy"] != "raw_base"
        or config["sampling_checkpoint_paths"]
        or config["run_cap_usd"] != "2.000000"
        or config["observation_mode"] != "candidate_set"
    ):
        raise RuntimeError("This runner permits only the approved raw-base A pilot.")
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    out = ROOT / "results/pilot_A"
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        transport = PilotTransport(
            config, directory, usage_path=out / "usage.jsonl", run_cap_usd="2.00"
        )
        transport.ledger.check_run(
            estimate_usd=proof["forecast_before_margin_usd"], max_cost_usd="2.00"
        )
        save_json(directory / "config.json", config)
        trainer = GuardedRL(transport)
        heartbeat = None
        heartbeat_stop = asyncio.Event()
        stop_requested = False
        tasks = []
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stop_requested
            stop_requested = True
            transport.failed = True

        loop.add_signal_handler(signal.SIGINT, stop)
        loop.add_signal_handler(signal.SIGTERM, stop)
        semaphore = asyncio.Semaphore(config["concurrent_games"])

        async def sample_game(record, *, kind, update, member=None):
            if kind == "train":
                scope = f"train/update-{update:02d}/member-{member}/"
                namespace = f"pilot-A-v1/train/member-{member}"
            else:
                scope = f"dev/checkpoint-{update:02d}/"
                namespace = "pilot-A-v1/development"
            key = scope + record["id"]
            dest = (
                directory
                / "games"
                / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            )
            if dest.exists():
                return json.loads(dest.read_text())
            async with semaphore:
                if transport.failed or stop_requested:
                    raise RuntimeError("New rollouts paused while pending work drains.")
                if heartbeat.done():
                    heartbeat.result()
                local = {**config, "sampling_seed_namespace": namespace}
                env = TableEnv(
                    record,
                    config["primary_model"],
                    local,
                    message_builder=candidate_messages,
                )
                trajectory = await do_single_rollout(
                    GuardedCompleter(SamplingScope(transport, scope), env), env
                )
                result = env.result()
                if not env.game.done:
                    raise RuntimeError("An RL rollout returned an unfinished game.")
                if (
                    abs(
                        sum(t.reward for t in trajectory.transitions) - result["reward"]
                    )
                    > 1e-10
                ):
                    raise RuntimeError(
                        "Cookbook return differs from exact outcome reward."
                    )
                result.update(
                    kind=kind,
                    update=update,
                    member=member,
                    policy_step=transport.active_step,
                    scope=scope,
                    sampling_seed_namespace=namespace,
                    policy="raw_base" if transport.active_step == 0 else "pilot_A",
                    trajectory=pack_trajectory(trajectory),
                )
                save_json(dest, result)
                return result

        async def sample_many(coroutines):
            nonlocal tasks
            tasks = [asyncio.create_task(c) for c in coroutines]
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            failures = [r for r in outcomes if isinstance(r, BaseException)]
            if failures:
                transport.failed = True
                network = next(
                    (r for r in failures if isinstance(r, NetworkInterruption)), None
                )
                raise network or failures[0]
            return outcomes

        async def develop(step):
            games = await sample_many(
                sample_game(r, kind="dev", update=step) for r in manifest["development"]
            )
            row = {"policy_step": step, **game_metrics(games)}
            save_json(out / f"development-{step:02d}.json", row)
            print(
                json.dumps({"development": row, "budget": transport.run_status()}),
                flush=True,
            )

        failure = None
        outcomes = []
        try:
            await transport.open(recover_pending=True)
            heartbeat = asyncio.create_task(transport.heartbeat(heartbeat_stop))
            model_id = await trainer.create_model(config)
            await trainer.base_sampler(config)
            await develop(0)
            updates = []
            checkpoints = {}
            stop_reason = "completed_16_updates"
            for row in manifest["training"]:
                step, record = row["update"], row["record"]
                games = await sample_many(
                    sample_game(record, kind="train", update=step, member=i)
                    for i in range(8)
                )
                trajectories = [unpack_trajectory(g["trajectory"]) for g in games]
                data, archive, returns, advantages = group_data(trajectories)
                if not data:
                    raise RuntimeError(
                        "No sampled action tokens were available for an update."
                    )
                if not np.allclose(
                    returns, [g["reward"] for g in games], atol=1e-12, rtol=0
                ):
                    raise RuntimeError(
                        "Group advantage inputs include unexpected reward."
                    )
                data_path = out / f"training-data-{step:02d}.json.gz"
                encoded = json.dumps(
                    archive, separators=(",", ":"), allow_nan=False
                ).encode()
                data_path.parent.mkdir(parents=True, exist_ok=True)
                compressed = gzip.compress(encoded, mtime=0)
                if data_path.exists() and data_path.read_bytes() != compressed:
                    raise RuntimeError("A resumed RL batch changed its training data.")
                temporary = data_path.with_suffix(".tmp")
                with temporary.open("wb") as f:
                    f.write(compressed)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporary, data_path)
                training = await trainer.update(model_id, step, data, archive, config)
                snapshots = await trainer.snapshot(model_id, step, config)
                if "checkpoint" in snapshots:
                    checkpoints[str(step)] = snapshots["checkpoint"]
                variance = float(np.var(returns))
                stats = {
                    "update": step,
                    "n": record["n"],
                    "start_state": record["id"],
                    **game_metrics(games),
                    **training,
                    "returns": returns,
                    "advantages": advantages,
                    "reward_variance": variance,
                    "win_variance": float(np.var([g["won"] for g in games])),
                    "nonzero_group_fraction": float(variance > 1e-12),
                }
                updates.append(stats)
                stats["cumulative_nonzero_group_fraction"] = float(
                    np.mean([u["nonzero_group_fraction"] for u in updates])
                )
                save_json(out / "learning_curve.json", {"updates": updates})
                print(
                    json.dumps(
                        {"training_update": stats, "budget": transport.run_status()}
                    ),
                    flush=True,
                )
                if step in config["development_checks"]:
                    await develop(step)
                if step == 4 and stats["cumulative_nonzero_group_fraction"] < 0.25:
                    stop_reason = "four_update_variance_stop"
                    break
            last = updates[-1]["update"]
            external = await trainer.export(model_id, last, config)
            adapter = await download_export(transport, external)
            await transport.finish()
            save_json(
                complete,
                {
                    "config_sha256": proof["config_sha256"],
                    "training_model_id": model_id,
                    "initialization": "raw_base_no_sft",
                    "updates": last,
                    "stop_reason": stop_reason,
                    "training_games": last * 8,
                    "development_games": 8
                    * (1 + sum(s <= last for s in config["development_checks"] if s)),
                    "checkpoints": checkpoints,
                    "external": external,
                    "adapter_files": adapter,
                    "snapshots": transport.state["snapshots"],
                    "run_budget": transport.run_status(),
                },
            )
        except Exception as exc:
            failure = exc
        finally:
            transport.failed = True
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            heartbeat_stop.set()
            if heartbeat:
                outcomes.extend(await asyncio.gather(heartbeat, return_exceptions=True))
            await transport.close()
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
        if stop_requested:
            raise RuntimeError(
                "Pilot stopped after draining HTTP work. All pending holds retained."
            )
        network = next(
            (r for r in outcomes if isinstance(r, NetworkInterruption)), None
        )
        if network:
            raise network
        if failure:
            raise failure


async def main():
    while True:
        try:
            return await run_once()
        except (NetworkInterruption, httpx.TransportError):
            print(
                "Network interrupted. Drained active work; reconnecting and collecting all saved sample/training futures before new submissions.",
                flush=True,
            )
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
