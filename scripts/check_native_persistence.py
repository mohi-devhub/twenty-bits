"""Save native weights, finish the source, and sample using a new service client."""

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tinker
from tinker import types

from twenty_bits.budget import BudgetError, now
from twenty_bits.native_checkpoints import save_native
from twenty_bits.rl_pilot import GuardedRL
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import GuardedTinker, save_json
from twenty_bits.worlds import ROOT


OUT = ROOT / "research/native_persistence_test.json"
PREFIX = "persistence-smoke-20261119"


def test_config(suffix):
    base = json.loads((ROOT / "experiments/main_A11.json").read_text())
    return {**base, "run_id": PREFIX + suffix,
            "display_name": "Twenty Bits native persistence test" + suffix,
            "rl_training_authorized": False, "training_authorized": False,
            "run_cap_usd": "0.700000", "ledger_phase": 4}


def transport(config):
    return GuardedTinker(config, ROOT / "runs" / config["run_id"],
                         usage_path=ROOT / "results/native_persistence_test/usage.jsonl",
                         run_cap_usd=config["run_cap_usd"])


async def save_and_sample():
    if OUT.exists():
        saved = json.loads(OUT.read_text())
        if saved.get("fresh_client_sample_passed"):
            print(json.dumps(saved), flush=True)
            return
    t = transport(test_config("-source"))
    trainer = GuardedRL(t)
    try:
        await t.open(recover_pending=True)
        model_id = await trainer.create_model(t.config)
        rows = {}
        for seq, kind in enumerate(("training", "sampler"), 1):
            # Reserve a full day at a deliberately conservative 64 GB per file.
            rows[kind] = await save_native(
                trainer, model_id, name=PREFIX, seq=seq, kind=kind,
                estimate="0.213334", maximum="0.320001",
            )
        save_json(OUT, {"saved_at": now(), "source_model_id": model_id,
                        "checkpoints": rows, "gradients_or_optimizer_steps": 0,
                        "console_verified": False, "test_checkpoints_deleted": False})
        await t.finish()
    finally:
        await t.close()
    config = test_config("-fresh-client")
    config["sampling_checkpoint_paths"] = {config["primary_model"]: rows["sampler"]["tinker_path"]}
    fresh = transport(config)
    try:
        await fresh.open(recover_pending=True)
        rendering = Rendering(config["primary_model"], config)
        prompt = rendering.prompt([{"role": "user", "content": "Reply with the word READY."}])
        result = await fresh.sample(
            model=config["primary_model"], key="native-restore-smoke",
            prompt=prompt, params=types.SamplingParams(max_tokens=16, temperature=0,
                                                       seed=191119, stop=rendering.renderer.get_stop_sequences()),
        )
        tokens = result["response"]["sequences"][0]["tokens"]
        if not tokens:
            raise BudgetError("Fresh-client native checkpoint sample was empty.")
        saved = json.loads(OUT.read_text())
        saved.update(fresh_client_sample_passed=True, source_finished_before_sample=True,
                     fresh_session_id=fresh.state["session_id"],
                     sample_text=rendering.tokenizer.decode(tokens),
                     sample_request_id=result["request_id"],
                     sample_cost_usd=result["actual_usd"], sample_output_tokens=len(tokens))
        save_json(OUT, saved)
        await fresh.finish()
        print(json.dumps(saved), flush=True)
    finally:
        await fresh.close()


async def cleanup():
    saved = json.loads(OUT.read_text())
    if saved.get("test_checkpoints_deleted"):
        print("Test checkpoints already deleted; no calls.")
        return
    if not saved.get("console_verified") or not saved.get("fresh_client_sample_passed"):
        raise BudgetError("Verify the test checkpoints in the console before deletion.")
    t = transport(test_config("-cleanup"))
    try:
        await t.open(recover_pending=True)
        for row in saved["checkpoints"].values():
            parsed = types.ParsedCheckpointTinkerPath.from_tinker_path(row["tinker_path"])
            if (parsed.training_run_id != saved["source_model_id"]
                or parsed.checkpoint_id.split("/")[-1] != PREFIX):
                raise BudgetError("Cleanup is restricted to this test's exact native paths.")
            await t.free("delete own persistence test " + parsed.checkpoint_id,
                lambda p=parsed: t.client.delete(
                    f"/api/v1/training_runs/{p.training_run_id}/checkpoints/{p.checkpoint_id}",
                    cast_to=type(None)))
        listing = await t.free("verify test deletion", lambda: t.client.weights.list(saved["source_model_id"]))
        if listing["checkpoints"]:
            raise BudgetError("The persistence test still has saved checkpoints.")
        saved.update(test_checkpoints_deleted=True, deletion_verified_at=now(), passed=True,
                     storage_holds_retained_pending_billing=True)
        save_json(OUT, saved)
        await t.finish()
        print(json.dumps(saved), flush=True)
    finally:
        await t.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    asyncio.run(cleanup() if args.cleanup else save_and_sample())
