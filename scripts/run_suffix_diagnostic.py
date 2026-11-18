"""Run only the approved auxiliary suffix-parser evaluation, capped at $1.50."""

import asyncio
from decimal import Decimal
import fcntl
import hashlib
import json
from pathlib import Path
import signal
import sys

import httpx
import tinker
from tinker_cookbook.rl.rollouts import do_single_rollout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_main_seed import metrics
from twenty_bits.budget import BudgetError
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.endpoint_restore import restore_A11_endpoint
from twenty_bits.guess_metrics import guess_state
from twenty_bits.model_player import GuardedCompleter, TableEnv
from twenty_bits.recovery import RecoveringTransport
from twenty_bits.rl_pilot import SamplingScope, pack_trajectory
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame
from twenty_bits.tinker_transport import NetworkInterruption, save_json
from twenty_bits.worlds import ROOT


async def run_once():
    block_path = ROOT / "research/A11_suffix_block.json"
    if block_path.exists() and json.loads(block_path.read_text())["active"]:
        print("Diagnostic blocked on endpoint restoration. No service calls.", flush=True)
        return
    out = ROOT / "results/A11_suffix_diagnostic"
    completion = out / "completion.json"
    if completion.exists():
        print("Auxiliary suffix diagnostic is complete. No service calls.", flush=True)
        return
    config_path = ROOT / "experiments/A11_suffix_diagnostic.json"
    config = json.loads(config_path.read_text())
    proof = json.loads(
        (ROOT / "research/A11_suffix_diagnostic_preflight.json").read_text()
    )
    assert (
        hashlib.sha256(config_path.read_bytes()).hexdigest() == proof["config_sha256"]
    )
    assert not config["is_primary_result"] and not config["rl_training_authorized"]
    for name, digest in proof["implementation_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    game_bytes = (ROOT / "experiments/A11_suffix_diagnostic_games.json").read_bytes()
    assert hashlib.sha256(game_bytes).hexdigest() == proof["games_sha256"]
    records = json.loads(game_bytes)
    assert len(records) == 168 and all(r["domain"] == "synthetic" for r in records)
    directory = ROOT / "runs" / config["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        transport = RecoveringTransport(
            config,
            directory,
            usage_path=out / "usage.jsonl",
            run_cap_usd="1.500000",
            registry_path=ROOT / "research/A11_suffix_diagnostic_replacements.json",
        )
        used = transport.run_status()
        residual = max(
            Decimal(0),
            Decimal("1.5") - Decimal(used["spent_usd"]) - Decimal(used["held_usd"]),
        )
        if Decimal(transport.ledger.status()["available_usd"]) < residual + Decimal(
            proof["remaining_U_with_margin_usd"]
        ):
            raise BudgetError(
                "Diagnostic ceiling plus remaining U margin no longer fits $50."
            )
        stop_event = asyncio.Event()
        heartbeat = None
        stopped = False
        tasks = []
        failure = None
        loop = asyncio.get_running_loop()

        def stop():
            nonlocal stopped
            stopped = True
            transport.failed = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop)
        semaphore = asyncio.Semaphore(16)

        async def play(record):
            key = "suffix_diagnostic/" + record["id"]
            dest = (
                directory
                / "games"
                / (hashlib.sha256(key.encode()).hexdigest() + ".json")
            )
            if dest.exists():
                return json.loads(dest.read_text())
            async with semaphore:
                if transport.failed or stopped:
                    raise RuntimeError(
                        "Diagnostic submissions stopped while futures drain."
                    )
                if heartbeat.done():
                    heartbeat.result()
                env = TableEnv(
                    record,
                    config["primary_model"],
                    config,
                    message_builder=candidate_messages,
                )
                env.game = SuffixDiagnosticGame(record)
                trajectory = await do_single_rollout(
                    GuardedCompleter(
                        SamplingScope(transport, "suffix_diagnostic/"), env
                    ),
                    env,
                )
                result = env.result()
                assert env.game.done
                assert (
                    abs(
                        sum(t.reward for t in trajectory.transitions) - result["reward"]
                    )
                    < 1e-10
                )
                result.update(
                    policy="A11_endpoint_suffix_DIAGNOSTIC_ONLY",
                    kind="diagnostic",
                    update=30,
                    is_primary_result=False,
                    policy_step=30,
                    scope="suffix_diagnostic/",
                    sampling_seed_namespace=config["sampling_seed_namespace"],
                    guess_state=guess_state(result, record),
                    trajectory=pack_trajectory(trajectory),
                )
                save_json(dest, result)
                print(
                    json.dumps(
                        {
                            "diagnostic_game": record["id"],
                            "won": result["won"],
                            "questions": result["questions"],
                            "mapped_identifiers": result["mapped_identifiers"],
                        }
                    ),
                    flush=True,
                )
                return result

        try:
            await transport.open(recover_pending=True)
            heartbeat = asyncio.create_task(transport.heartbeat(stop_event))
            restored = await restore_A11_endpoint(transport, config)
            tasks = [asyncio.create_task(play(r)) for r in records]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            errors = [r for r in results if isinstance(r, BaseException)]
            if errors:
                raise next(
                    (e for e in errors if isinstance(e, NetworkInterruption)), errors[0]
                )
            await transport.finish()
            save_json(
                completion,
                {
                    "diagnostic_only": True,
                    "is_primary_result": False,
                    "games": 168,
                    "config_sha256": proof["config_sha256"],
                    "restored_adapter": restored,
                    "sampler": transport.state["snapshots"]["30"],
                    "run_budget": transport.run_status(),
                    "summary": metrics(results),
                    "next_stage": "Approved A23 only; B41 remains gated.",
                },
            )
        except Exception as exc:
            failure = exc
        finally:
            transport.failed = True
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            stop_event.set()
            if heartbeat:
                outcomes.extend(await asyncio.gather(heartbeat, return_exceptions=True))
            await transport.close()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
        if stopped:
            raise RuntimeError("Diagnostic stopped after draining active HTTP work.")
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
                "Diagnostic network interrupted; drain and recover existing IDs before new work.",
                flush=True,
            )
            await asyncio.sleep(1)
        except tinker.APIStatusError as exc:
            if exc.status_code == 429 or exc.status_code >= 500:
                await asyncio.sleep(1)
                continue
            raise


if __name__ == "__main__":
    asyncio.run(main())
