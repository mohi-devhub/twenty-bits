"""Named native checkpoints survive their source service session."""

from decimal import Decimal

from tinker import types

from .budget import BudgetError
from .rl_pilot import GuardedRL, sequence_ids
from .tinker_transport import save_json


STORAGE_RATE = Decimal("0.10")  # USD per decimal GB per month, paid-plan bound.


def storage_estimate(size_bytes, months=1):
    if size_bytes <= 0 or months <= 0:
        raise ValueError("Storage estimates need a positive size and duration.")
    return Decimal(size_bytes) / Decimal(10**9) * STORAGE_RATE * Decimal(months)


def require_checkpoint(row, model_id, kind):
    prefix = f"tinker://{model_id}/{'weights' if kind == 'training' else 'sampler_weights'}/"
    if (
        row.get("checkpoint_type") != kind
        or not row.get("tinker_path", "").startswith(prefix)
        or not row.get("size_bytes", 0)
        or "expires_at" not in row
        or row.get("expires_at") is not None
    ):
        raise BudgetError("Native checkpoint must have the expected owner/type, bytes and no expiry.")
    return row


async def save_native(trainer, model_id, *, name, seq, kind, estimate, maximum):
    t = trainer.transport
    request_type = types.SaveWeightsRequest if kind == "training" else types.SaveWeightsForSamplerRequest
    request = request_type(model_id=model_id, seq_id=seq, path=name, ttl_seconds=None)
    send = t.client.weights.save if kind == "training" else t.client.weights.save_for_sampler
    result = await trainer.operation(
        f"permanent-{kind}-{name}",
        request.model_dump(mode="json"),
        lambda: send(request=request, max_retries=0),
        request_id=f"{model_id}:{seq}",
        estimate=str(estimate), maximum=str(maximum), storage=True,
    )
    listing = await t.free(f"verify native {kind} checkpoint", lambda: t.client.weights.list(model_id))
    path = result["response"]["path"]
    matches = [r for r in listing["checkpoints"] if r["tinker_path"] == path]
    if len(matches) != 1:
        raise BudgetError("The completed save is absent from the native checkpoint listing.")
    row = require_checkpoint(matches[0], model_id, kind)
    evidence = {
        **row,
        "storage_rate_usd_per_GB_month": str(STORAGE_RATE),
        "monthly_paid_plan_usd": str(storage_estimate(row["size_bytes"])),
        "billing_reconciled": False,
        "retention": "no expiry; hold is a priced reserve, not a settled invoice",
    }
    t.ledger._update(result["entry_id"], lambda entry: entry.update(checkpoint=evidence))
    result["checkpoint"] = evidence
    save_json(t.directory / "checkpoints" / f"{kind}-{name}.json", result)
    return evidence


class PersistentEndpointRL(GuardedRL):
    async def snapshot(self, model_id, step, config):
        if step not in config["kept_checkpoints"]:
            return await super().snapshot(model_id, step, config)
        if config["kept_checkpoints"] != [30] or step != 30 or config["checkpoint_ttl_seconds"] is not None:
            raise BudgetError("Only the scheduled endpoint is saved permanently.")
        response = await super().snapshot(model_id, step, {**config, "kept_checkpoints": []})
        seq = sequence_ids(step, config["kept_checkpoints"])["named"]
        saved = {}
        for offset, kind in enumerate(("training", "sampler")):
            pricing = config["permanent_storage"][kind]
            saved[kind] = await save_native(
                self, model_id, name=f"{config['checkpoint_prefix']}-step-{step:02d}",
                seq=seq + offset, kind=kind,
                estimate=pricing["estimated_usd"], maximum=pricing["maximum_usd"],
            )
        response["checkpoint"] = saved
        return response
