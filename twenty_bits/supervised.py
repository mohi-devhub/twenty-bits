"""Guarded cross-entropy warm start using pinned cookbook supervision helpers."""

import asyncio
from decimal import Decimal
import gzip
import hashlib
import json

import numpy as np
import tinker
from tinker import types
from tinker_cookbook.supervised.common import datum_from_model_input_weights

from .budget import BudgetError, money, now
from .tinker_rendering import Rendering
from .tinker_transport import NetworkInterruption, rates, save_json
from .worlds import ROOT, training_game


def qualification_records():
    return [
        training_game(n, 600000 + i, seed=20261120, noise=0)
        for n in (4, 8)
        for i in range(16)
    ]


def supervised_data(config):
    path = ROOT / config["training_data"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != config["training_data_sha256"]:
        raise BudgetError("The approved SFT examples changed.")
    rendering = Rendering(config["primary_model"], config)
    data = []
    for line in gzip.open(path, "rt"):
        example = json.loads(line)
        messages = example["messages"]
        prompt = rendering.prompt(messages[:-1]).to_ints()
        tokens, weights = rendering.renderer.build_supervised_example(messages)
        assert tokens.to_ints()[: len(prompt)] == prompt
        assert not weights[: len(prompt)].any()
        datum = datum_from_model_input_weights(tokens, weights, reduction="mean")
        assert datum.model_input.length == tokens.length - 1
        assert np.isclose(sum(datum.loss_fn_inputs["weights"].data), 1)
        data.append(datum)
    assert len(data) == config["examples"]
    assert sum(d.model_input.length for d in data) == config["tokens_per_epoch"]
    return data


class GuardedSupervised:
    def __init__(self, transport):
        self.transport = transport

    async def operation(
        self, key, payload, send, *, estimate="0", maximum="0", storage=False
    ):
        """Persist one dispatch, then collect its receipt and original future."""
        t = self.transport
        path = t.directory / "operations" / f"{key}.json"
        signature = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        if path.exists():
            journal = json.loads(path.read_text())
            if journal["signature"] != signature:
                raise BudgetError("A resumed training operation changed its inputs.")
            if journal.get("completed") and (journal.get("settled") or storage):
                return journal
            if not journal.get("request_id"):
                raise BudgetError(
                    "Dispatched training work has no receipt. Keep its hold; do not resubmit."
                )
        else:
            operation = "SFT " + key
            journal = {
                "key": key,
                "signature": signature,
                "payload": payload,
                "storage": storage,
                "estimated_usd": estimate,
                "maximum_usd": maximum,
            }

            def submit():
                entries = [
                    e
                    for e in t.ledger.status()["entries"]
                    if e["operation"] == t.operation_prefix + operation
                    and e["state"] == "dispatching"
                ]
                if len(entries) != 1:
                    raise BudgetError("Training dispatch needs one unique reservation.")
                journal["entry_id"] = entries[0]["id"]
                journal["saved_before_dispatch_at"] = now()
                save_json(path, journal)
                return asyncio.create_task(send())

            if t.failed:
                raise BudgetError(
                    "Training stopped until pending operations are recovered."
                )
            _, task = t.call(
                submit, operation=operation, estimate_usd=estimate, max_cost_usd=maximum
            )
            try:
                receipt = await task
            except tinker.APIConnectionError as exc:
                t.failed = True
                raise NetworkInterruption(
                    "Reconnect and recover the saved training operation before new work."
                ) from exc
            journal["receipt"] = receipt.model_dump(mode="json")
            journal["request_id"] = receipt.request_id
            save_json(path, journal)
            t.ledger.attach_request_id(journal["entry_id"], receipt.request_id)
        entry = next(
            e for e in t.ledger.status()["entries"] if e["id"] == journal["entry_id"]
        )
        if entry["state"] != "settled":
            t.ledger.attach_request_id(journal["entry_id"], journal["request_id"])
        journal.setdefault("collection_started_at", now())
        save_json(path, journal)
        response = journal.get("response")
        if response is None:
            response = await t.poll(journal["request_id"])
        journal.update(response=response, response_received_at=now(), completed=True)
        save_json(path, journal)
        if storage:
            journal["cost_pending"] = (
                "Checkpoint storage; retain the hold until billing reconciliation. TTL is bounded."
            )
        else:
            if entry["state"] == "settled":
                if money(entry["actual_usd"]) != money(maximum):
                    raise BudgetError(
                        "Settled training cost differs from its saved operation."
                    )
            else:
                evidence = t.evidence(
                    journal["entry_id"],
                    {
                        "operation": "SFT " + key,
                        "request_id": journal["request_id"],
                        "actual_usd": maximum,
                        "billing_basis": "Submitted full-context training tokens at the published rate, rounded up; metadata and optimizer operations have zero token charge. Invoice reconciliation pending.",
                        "payload": payload,
                    },
                )
                t.ledger.settle(
                    journal["entry_id"], actual_usd=maximum, evidence=evidence
                )
            journal.update(actual_usd=maximum, settled=True)
        save_json(path, journal)
        return journal

    async def create_model(self, config):
        t = self.transport
        request = types.CreateModelRequest(
            session_id=t.state["session_id"],
            model_seq_id=0,
            base_model=config["primary_model"],
            lora_config=types.LoraConfig(**config["lora"]),
            optimizer_config=types.AdamOptimizerConfig(),
            user_metadata={
                "run": config["run_id"],
                "objective": "format-only cross_entropy",
            },
        )
        journal = await self.operation(
            "create-model",
            request.model_dump(mode="json"),
            lambda: t.client.models.create(request=request),
        )
        model_id = journal["response"]["model_id"]
        if t.state.get("training_model_id") not in (None, model_id):
            raise BudgetError("Training model identity changed.")
        t.state["training_model_id"] = model_id
        save_json(t.state_path, t.state)
        return model_id

    async def batch(self, model_id, index, indices, data, config):
        t = self.transport
        batch = [data[i] for i in indices]
        token_count = sum(d.model_input.length for d in batch)
        cost = str(
            money(
                Decimal(token_count)
                * rates(config["primary_model"])["train"]
                / 1_000_000
            )
        )
        payload = {
            "model_id": model_id,
            "seq_id": index * 2 + 1,
            "dataset_sha256": config["training_data_sha256"],
            "indices": indices,
            "tokens": token_count,
            "loss_fn": "cross_entropy",
            "weight_reduction": "mean",
        }
        request = types.ForwardBackwardRequest(
            model_id=model_id,
            seq_id=index * 2 + 1,
            forward_backward_input=types.ForwardBackwardInput(
                data=batch, loss_fn="cross_entropy"
            ),
        )
        forward = await self.operation(
            f"forward-{index:03d}",
            payload,
            lambda: t.client.training.forward_backward(request=request),
            estimate=cost,
            maximum=cost,
        )
        outputs = forward["response"]["loss_fn_outputs"]
        assert len(outputs) == len(batch)
        losses = []
        for output, datum in zip(outputs, batch):
            logps = np.asarray(output["logprobs"]["data"])
            weights = np.asarray(datum.loss_fn_inputs["weights"].data)
            assert len(logps) == len(weights) and np.isfinite(logps).all()
            losses.append(float(-(logps * weights).sum() / weights.sum()))
        optim = types.OptimStepRequest(
            model_id=model_id,
            seq_id=index * 2 + 2,
            optim_params=types.AdamParams(**config["adam"]),
        )
        await self.operation(
            f"optim-{index:03d}",
            optim.model_dump(mode="json"),
            lambda: t.client.training.optim_step(request=optim),
        )
        return {
            "update": index + 1,
            "examples": len(indices),
            "training_tokens": token_count,
            "action_nll": float(np.mean(losses)),
            "gradient_usd": cost,
            "forward_request_id": forward["request_id"],
        }

    async def sampler(self, model_id, config):
        t = self.transport
        seq = config["updates"] * 2 + 1
        request = types.SaveWeightsForSamplerRequest(
            model_id=model_id, seq_id=seq, sampling_session_seq_id=0, kind="snapshot"
        )
        saved = await self.operation(
            "sampler-snapshot",
            request.model_dump(mode="json"),
            lambda: t.client.weights.save_for_sampler(request=request, max_retries=0),
        )
        sampler_id = saved["response"]["sampling_session_id"]
        existing = t.state["samplers"].get(config["primary_model"])
        if existing is None:
            t.state["samplers"][config["primary_model"]] = {
                "id": sampler_id,
                "next_seq": 0,
            }
        elif existing["id"] != sampler_id:
            raise BudgetError(
                "Qualification sampler does not match the trained snapshot."
            )
        t.state["next_sampler"] = max(t.state["next_sampler"], 1)
        save_json(t.state_path, t.state)
        return sampler_id

    async def save_checkpoints(self, model_id, config):
        t = self.transport
        seq = config["updates"] * 2 + 2
        native = types.SaveWeightsForSamplerRequest(
            model_id=model_id,
            seq_id=seq,
            path="format-warmstart",
            ttl_seconds=config["checkpoint_ttl_seconds"],
        )
        a = await self.operation(
            "native-checkpoint",
            native.model_dump(mode="json"),
            lambda: t.client.weights.save_for_sampler(request=native, max_retries=0),
            estimate=".02",
            maximum=".05",
            storage=True,
        )
        external = types.SaveWeightsExternalRequest(
            model_id=model_id,
            seq_id=seq + 1,
            path="format-warmstart",
            ttl_seconds=config["checkpoint_ttl_seconds"],
        )
        b = await self.operation(
            "external-checkpoint",
            external.model_dump(mode="json"),
            lambda: t.client.weights.save_external(request=external, max_retries=0),
            estimate=".02",
            maximum=".05",
            storage=True,
        )
        return {"native": a["response"], "external": b["response"]}
