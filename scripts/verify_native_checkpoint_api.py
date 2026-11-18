"""List saved test checkpoints through the API, then sample in a fresh client."""

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tinker import types

from scripts.check_native_persistence import OUT, test_config, transport
from twenty_bits.budget import BudgetError, now
from twenty_bits.native_checkpoints import require_checkpoint
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


EVIDENCE = ROOT / "research/native_persistence_api_verification.json"


async def main():
    if EVIDENCE.exists() and json.loads(EVIDENCE.read_text()).get("fresh_client_sample_passed"):
        print(EVIDENCE.read_text())
        return
    saved = json.loads(OUT.read_text())
    if saved["test_checkpoints_deleted"]:
        raise BudgetError("The existing persistence test files have been deleted.")
    source_state = json.loads((ROOT / "runs/persistence-smoke-20261119-source/sessions.json").read_text())
    if not source_state["finished"]:
        raise BudgetError("Finish the original save session before the fresh-client test.")
    wanted = {row["tinker_path"]: kind for kind, row in saved["checkpoints"].items()}
    config = test_config("-api-verification")
    config["sampling_checkpoint_paths"] = {
        config["primary_model"]: saved["checkpoints"]["sampler"]["tinker_path"]
    }
    fresh = transport(config)
    evidence = {"requested_at": now(), "browser_used": False,
                "listing_endpoint": "/api/v1/checkpoints", "checkpoint_rows": [],
                "list_pages": [], "user_console_confirmation_pending": True,
                "A23_started": False, "test_files_deleted": False}
    try:
        await fresh.open(recover_pending=True)
        offset, limit = 0, 100
        while True:
            # Keep raw JSON values instead of converting API timestamps or sizes.
            page = await fresh.free(
                f"list user checkpoints offset {offset}",
                lambda start=offset: fresh.client.get(
                    "/api/v1/checkpoints",
                    options={"params": {"limit": limit, "offset": start}},
                    cast_to=dict[str, Any],
                ),
            )
            rows = page["checkpoints"]
            evidence["list_pages"].append({"offset": offset, "returned": len(rows), "cursor": page.get("cursor")})
            evidence["checkpoint_rows"].extend(row for row in rows if row["tinker_path"] in wanted)
            cursor = page.get("cursor")
            if (cursor and offset + limit >= cursor["total_count"]) or (not cursor and len(rows) < limit):
                break
            offset += limit
        evidence["listing_collected_at"] = now()
        save_json(EVIDENCE, evidence)
        if {r["tinker_path"] for r in evidence["checkpoint_rows"]} != set(wanted) or len(evidence["checkpoint_rows"]) != 2:
            raise BudgetError("Both exact test files must appear in the user's checkpoint listing.")
        for row in evidence["checkpoint_rows"]:
            require_checkpoint(row, saved["source_model_id"], wanted[row["tinker_path"]])
            if row.get("deleted_at") is not None:
                raise BudgetError("A listed test checkpoint has been deleted.")
        rendering = Rendering(config["primary_model"], config)
        prompt = rendering.prompt([{"role": "user", "content": "Reply with the word READY."}])
        sample = await fresh.sample(
            model=config["primary_model"], key="api-listed-native-restore-smoke",
            prompt=prompt,
            params=types.SamplingParams(max_tokens=16, temperature=0, seed=191119,
                                       stop=rendering.renderer.get_stop_sequences()),
        )
        tokens = sample["response"]["sequences"][0]["tokens"]
        if not tokens:
            raise BudgetError("The fresh-client sample was empty.")
        evidence.update(
            fresh_client_sample_passed=True,
            sample_collected_at=now(),
            source_finished_before_listing_and_sampling=True,
            fresh_session_id=fresh.state["session_id"],
            sampler_path=config["sampling_checkpoint_paths"][config["primary_model"]],
            sample_request_id=sample["request_id"],
            request_id_saved_before_dispatch=sample["request_id_saved_before_dispatch"],
            raw_sample_text=rendering.tokenizer.decode(tokens),
            output_tokens=len(tokens), sample_cost_usd=sample["actual_usd"],
        )
        save_json(EVIDENCE, evidence)
        saved.update(api_listing_verification=str(EVIDENCE.relative_to(ROOT)),
                     api_verified_at=evidence["sample_collected_at"],
                     user_console_confirmation_pending=True)
        save_json(OUT, saved)
        await fresh.finish()
        print(json.dumps(evidence, indent=2))
    finally:
        await fresh.close()


if __name__ == "__main__":
    asyncio.run(main())
