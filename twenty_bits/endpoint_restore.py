"""Reconnect to the exact immutable A11 sampling snapshot for auxiliary inference."""

import hashlib
import json
from typing import Any

from .budget import BudgetError
from .tinker_transport import save_json
from .worlds import ROOT


async def restore_A11_endpoint(transport, config):
    if config.get("is_primary_result") is not False or config["rl_training_authorized"]:
        raise BudgetError("This endpoint access is restricted to auxiliary inference.")
    source = json.loads((ROOT / "results/main_A11/completion.json").read_text())
    session_path = ROOT / "runs/main-U-A11-v1/sessions.json"
    if session_path.exists() and json.loads(session_path.read_text())["finished"]:
        raise BudgetError(
            "A11's source ServiceClient is finished. Metadata does not prove usable weights; restore the local adapter or supply a live endpoint checkpoint."
        )
    snapshot = source["snapshots"]["30"]
    info = await transport.free(
        "join the immutable A11 endpoint sampler",
        lambda: transport.client.get(
            "/api/v1/samplers/" + snapshot["id"], cast_to=dict[str, Any]
        ),
    )
    if (
        info["sampler_id"] != snapshot["id"]
        or info["base_model"] != config["primary_model"]
    ):
        raise BudgetError("The hosted endpoint sampler differs from A11.")
    if not info["model_path"].startswith(
        "tinker://" + source["training_model_id"] + "/sampler_weights/"
    ):
        raise BudgetError("The immutable sampler belongs to another model.")
    for name, expected in config["source_adapter_files"].items():
        data = (ROOT / "runs/main-U-A11-v1/adapter" / name).read_bytes()
        if (
            len(data) != expected["bytes"]
            or hashlib.sha256(data).hexdigest() != expected["sha256"]
        ):
            raise ValueError("The archived A11 adapter identity changed.")
    saved = transport.state.setdefault("snapshots", {}).get("30")
    prefix = snapshot["id"] + ":"
    used = [
        int(e["request_id"][len(prefix) :])
        for e in transport.ledger.status()["entries"]
        if (e.get("request_id") or "").startswith(prefix)
    ]
    next_seq = max(snapshot["next_seq"], max(used, default=-1) + 1)
    if saved is None:
        transport.state["snapshots"]["30"] = {
            "id": snapshot["id"],
            "next_seq": next_seq,
            "policy_step": 30,
            "source_adapter_sha256": config["source_adapter_files"][
                "adapter_model.safetensors"
            ]["sha256"],
        }
        save_json(transport.state_path, transport.state)
    elif saved["id"] != snapshot["id"] or saved["next_seq"] < next_seq:
        raise BudgetError("An endpoint counter differs from its durable request IDs.")
    transport.active_step = 30
    return {
        "source_sampler": info,
        "initial_next_sequence": next_seq,
        "checkpoint_file_expired": True,
        "weights_reloaded_or_trained": False,
        "method": "Reuse the same immutable hosted A11 sampler; allocate new request sequences after every existing ledger ID. No primary output is reused or rescored.",
    }
