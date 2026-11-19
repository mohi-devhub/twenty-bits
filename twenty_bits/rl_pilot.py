"""Outcome-only groups, cookbook training data and durable RL operations."""

import asyncio
from dataclasses import replace
from decimal import Decimal
import hashlib
import json

import numpy as np
import tinker
from tinker import types
from tinker_cookbook.completers import TokensWithLogprobs
from tinker_cookbook.rl.data_processing import assemble_training_data
from tinker_cookbook.rl.types import Trajectory, TrajectoryGroup, Transition
import torch

from .budget import BudgetError, money, now
from .tinker_transport import GuardedTinker, NetworkInterruption, rates, save_json


def standardized_advantages(returns):
    values = np.asarray(returns, dtype=np.float64)
    if values.shape != (8,) or not np.isfinite(values).all():
        raise ValueError("A pilot group needs eight finite total returns.")
    if np.ptp(values) < 1e-12:
        return np.zeros_like(values)
    return (values - values.mean()) / (values.std(ddof=0) + 1e-8)


def sequence_ids(step, kept):
    start = 3 * (step - 1) + sum(k < step for k in kept) + 1
    return {
        "forward": start,
        "optim": start + 1,
        "snapshot": start + 2,
        "named": start + 3 if step in kept else None,
    }


def pack_trajectory(trajectory):
    return [
        {
            "ob": t.ob.to_ints(),
            "tokens": t.ac.tokens,
            "logprobs": t.ac.logprobs,
            "sequence_id": t.ac.sequence_id,
            "stop_reason": t.ac.stop_reason,
            "reward": t.reward,
            "episode_done": t.episode_done,
            "metrics": t.metrics,
        }
        for t in trajectory.transitions
    ]


def unpack_trajectory(rows):
    return Trajectory(
        transitions=[
            Transition(
                ob=tinker.ModelInput.from_ints(r["ob"]),
                ac=TokensWithLogprobs(
                    tokens=r["tokens"],
                    maybe_logprobs=r["logprobs"],
                    sequence_id=r["sequence_id"],
                    stop_reason=r["stop_reason"],
                ),
                reward=r["reward"],
                episode_done=r["episode_done"],
                metrics=r["metrics"],
            )
            for r in rows
        ],
        final_ob=tinker.ModelInput.empty(),
    )


def group_data(trajectories):
    group = TrajectoryGroup(
        trajectories_G=trajectories,
        final_rewards_G=[0.0] * 8,
        metrics_G=[{} for _ in range(8)],
    )
    returns = group.get_total_rewards()
    advantages = standardized_advantages(returns)
    data, metadata = assemble_training_data(
        [group],
        [torch.tensor(advantages, dtype=torch.float32)],
        include_provenance=False,
    )
    archive = []
    for datum, meta in zip(data, metadata):
        mask = np.asarray(datum.loss_fn_inputs["mask"].data)
        adv = np.asarray(datum.loss_fn_inputs["advantages"].data)
        logps = np.asarray(datum.loss_fn_inputs["logprobs"].data)
        assert not np.any(adv[mask == 0]) and not np.any(logps[mask == 0])
        assert np.isfinite(logps).all() and np.isfinite(adv).all()
        assert np.allclose(adv[mask == 1], advantages[meta["traj_idx"]], atol=1e-6)
        archive.append(
            {
                "input_tokens": datum.model_input.to_ints(),
                "loss_fn_inputs": {
                    k: {"data": v.data, "dtype": v.dtype, "shape": v.shape}
                    for k, v in datum.loss_fn_inputs.items()
                    if k != "mask"
                },
                "training_mask": mask.tolist(),
                "metadata": meta,
            }
        )
    assert sum(sum(row["training_mask"]) for row in archive) == sum(
        len(t.ac.tokens) for trajectory in trajectories for t in trajectory.transitions
    )
    # Match the cookbook train_step boundary: mask is an audit field, while
    # zero advantages suppress loss on all environment and prompt positions.
    clean = [
        replace(
            d, loss_fn_inputs={k: v for k, v in d.loss_fn_inputs.items() if k != "mask"}
        )
        for d in data
    ]
    return clean, archive, returns, advantages.tolist()


class SamplingScope:
    def __init__(self, transport, prefix):
        self.transport, self.prefix = transport, prefix

    async def sample(self, *, key, **kwargs):
        return await self.transport.sample(key=self.prefix + key, **kwargs)


class PilotTransport(GuardedTinker):
    """Keep one durable sequence counter per immutable policy snapshot."""

    active_step = 0

    async def sampler(self, model):
        if model != self.config["primary_model"]:
            raise BudgetError("Pilot sampling is restricted to its primary model.")
        saved = self.state.get("snapshots", {}).get(str(self.active_step))
        if saved is None:
            raise BudgetError("The requested immutable policy snapshot is missing.")
        return saved

    async def collect_pending(self):
        outcomes = await asyncio.gather(
            super().collect_pending(), GuardedRL(self).recover(), return_exceptions=True
        )
        failures = [r for r in outcomes if isinstance(r, BaseException)]
        if failures:
            self.failed = True
            network = next(
                (r for r in failures if isinstance(r, NetworkInterruption)), None
            )
            raise network or failures[0]


class GuardedRL:
    def __init__(self, transport):
        self.transport = transport

    async def collect(self, journal, path):
        t = self.transport
        entry = t.ledger.get(journal["entry_id"])
        if entry["state"] != "settled":
            t.ledger.attach_request_id(journal["entry_id"], journal["request_id"])
        journal.setdefault("collection_started_at", now())
        save_json(path, journal)
        if "response" not in journal:
            journal["response"] = await t.poll(journal["request_id"])
            journal["response_received_at"] = now()
            save_json(path, journal)
        journal["completed"] = True
        if journal["storage"]:
            journal["cost_pending"] = (
                "Bounded checkpoint storage; retain hold until billing reconciliation. Future result collected."
            )
        else:
            maximum = journal["maximum_usd"]
            if entry["state"] == "settled":
                if money(entry["actual_usd"]) != money(maximum):
                    raise BudgetError("Recovered RL cost disagrees with settlement.")
            else:
                evidence = t.evidence(
                    journal["entry_id"],
                    {
                        "operation": "RL " + journal["key"],
                        "request_id": journal["request_id"],
                        "actual_usd": maximum,
                        "payload": journal["payload"],
                        "billing_basis": "Full submitted datum input tokens at the pinned training rate, rounded upward. Optimizer/metadata have zero token charge. Invoice pending.",
                    },
                )
                t.ledger.settle(
                    journal["entry_id"], actual_usd=maximum, evidence=evidence
                )
            journal.update(settled=True, actual_usd=maximum)
        save_json(path, journal)
        return journal

    async def recover(self):
        pending = []
        for path in sorted((self.transport.directory / "operations").glob("*.json")):
            journal = json.loads(path.read_text())
            if journal.get("completed") and (
                journal.get("settled") or journal["storage"]
            ):
                continue
            pending.append((journal, path))
        outcomes = await asyncio.gather(
            *(self.collect(j, p) for j, p in pending), return_exceptions=True
        )
        errors = [r for r in outcomes if isinstance(r, BaseException)]
        if errors:
            network = next(
                (r for r in errors if isinstance(r, NetworkInterruption)), None
            )
            raise network or errors[0]

    async def operation(
        self,
        key,
        payload,
        send,
        *,
        request_id,
        estimate="0",
        maximum="0",
        storage=False,
    ):
        t = self.transport
        path = t.directory / "operations" / (key + ".json")
        signature = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        if path.exists():
            journal = json.loads(path.read_text())
            if journal["signature"] != signature or journal["request_id"] != request_id:
                raise BudgetError("A resumed RL operation changed its declared inputs.")
            if journal.get("completed") and (journal.get("settled") or storage):
                return journal
        else:
            operation = "RL " + key
            journal = {
                "key": key,
                "payload": payload,
                "signature": signature,
                "request_id": request_id,
                "request_id_saved_before_dispatch": True,
                "storage": storage,
                "maximum_usd": maximum,
                "estimated_usd": estimate,
            }

            def submit():
                entries = [
                    e
                    for e in t.ledger.entries(
                        operation=t.operation_prefix + operation, states={"dispatching"}
                    )
                ]
                if len(entries) != 1:
                    raise BudgetError("RL dispatch needs one unique reservation.")
                journal["entry_id"] = entries[0]["id"]
                journal["saved_before_dispatch_at"] = now()
                save_json(path, journal)
                t.ledger.attach_request_id(journal["entry_id"], request_id)
                return asyncio.create_task(send())

            if t.failed:
                raise BudgetError(
                    "Pause RL mutations until every pending future is collected."
                )
            _, task = t.call(
                submit, operation=operation, estimate_usd=estimate, max_cost_usd=maximum
            )
            try:
                receipt = await task
            except tinker.APIConnectionError as exc:
                t.failed = True
                raise NetworkInterruption(
                    "Reconnect and collect the saved RL request ID; never resubmit."
                ) from exc
            journal["receipt"] = receipt.model_dump(mode="json")
            save_json(path, journal)
            if receipt.request_id != request_id:
                t.failed = True
                raise BudgetError(
                    "RL receipt differs from its pre-dispatch request ID. Hold retained."
                )
        return await self.collect(journal, path)

    async def create_model(self, config):
        t = self.transport
        model_id = t.state["session_id"] + ":train:0"
        request = types.CreateModelRequest(
            session_id=t.state["session_id"],
            model_seq_id=0,
            base_model=config["primary_model"],
            lora_config=types.LoraConfig(**config["lora"]),
            optimizer_config=types.AdamOptimizerConfig(),
            user_metadata={
                "run": config["run_id"],
                "objective": "outcome-only group-standardized importance_sampling",
                "initialization": "raw_base_no_sft",
            },
        )
        result = await self.operation(
            "create-model",
            request.model_dump(mode="json"),
            lambda: t.client.models.create(request=request),
            request_id=model_id + ":0",
        )
        if result["response"]["model_id"] != model_id:
            raise BudgetError(
                "The training model identity differs from the saved plan."
            )
        t.state["training_model_id"] = model_id
        save_json(t.state_path, t.state)
        return model_id

    async def base_sampler(self, config):
        t = self.transport
        if "0" not in t.state.get("snapshots", {}):
            request = types.CreateSamplingSessionRequest(
                session_id=t.state["session_id"],
                sampling_session_seq_id=0,
                base_model=config["primary_model"],
            )
            result = await t.free(
                "create raw-base pilot sampler",
                lambda: t.client.service.create_sampling_session(request=request),
            )
            t.state.setdefault("snapshots", {})["0"] = {
                "id": result["sampling_session_id"],
                "next_seq": 0,
                "policy_step": 0,
                "initialization": "raw_base",
            }
            save_json(t.state_path, t.state)
        t.active_step = 0

    async def update(self, model_id, update, data, archive, config):
        t = self.transport
        seq = sequence_ids(update, config["kept_checkpoints"])
        tokens = sum(d.model_input.length for d in data)
        cost = str(
            money(Decimal(tokens) * rates(config["primary_model"])["train"] / 1_000_000)
        )
        request = types.ForwardBackwardRequest(
            model_id=model_id,
            seq_id=seq["forward"],
            forward_backward_input=types.ForwardBackwardInput(
                data=data, loss_fn="importance_sampling"
            ),
        )
        payload = {
            "model_id": model_id,
            "seq_id": seq["forward"],
            "tokens": tokens,
            "loss_fn": "importance_sampling",
            "data_sha256": hashlib.sha256(
                json.dumps(archive, sort_keys=True).encode()
            ).hexdigest(),
        }
        forward = await self.operation(
            f"forward-{update:02d}",
            payload,
            lambda: t.client.training.forward_backward(request=request),
            request_id=f"{model_id}:{seq['forward']}",
            estimate=cost,
            maximum=cost,
        )
        diagnostics = []
        if len(forward["response"]["loss_fn_outputs"]) != len(archive):
            raise ValueError("The server returned the wrong number of RL datums.")
        for output, row in zip(forward["response"]["loss_fn_outputs"], archive):
            logps = np.asarray(output["logprobs"]["data"])
            mask = np.asarray(row["training_mask"], dtype=bool)
            before = np.asarray(row["loss_fn_inputs"]["logprobs"]["data"])
            if logps.shape != before.shape or not np.isfinite(logps).all():
                raise ValueError("Invalid returned training log probabilities.")
            diagnostics.extend((logps[mask] - before[mask]).tolist())
        optim = types.OptimStepRequest(
            model_id=model_id,
            seq_id=seq["optim"],
            optim_params=types.AdamParams(**config["adam"]),
        )
        await self.operation(
            f"optim-{update:02d}",
            optim.model_dump(mode="json"),
            lambda: t.client.training.optim_step(request=optim),
            request_id=f"{model_id}:{seq['optim']}",
        )
        return {
            "training_tokens": tokens,
            "datums": len(data),
            "gradient_usd": cost,
            "forward_request_id": forward["request_id"],
            "mean_train_minus_sample_logprob": float(np.mean(diagnostics)),
            "max_abs_train_minus_sample_logprob": float(np.max(np.abs(diagnostics))),
            "server_metrics": forward["response"].get("metrics", {}),
        }

    async def snapshot(self, model_id, step, config):
        t = self.transport
        keep = step in config["kept_checkpoints"]
        seq = sequence_ids(step, config["kept_checkpoints"])
        request = types.SaveWeightsForSamplerRequest(
            model_id=model_id,
            seq_id=seq["snapshot"],
            sampling_session_seq_id=step,
            kind="snapshot",
        )
        result = await self.operation(
            f"snapshot-{step:02d}",
            request.model_dump(mode="json"),
            lambda: t.client.weights.save_for_sampler(request=request, max_retries=0),
            request_id=f"{model_id}:{seq['snapshot']}",
        )
        identity = result["response"]["sampling_session_id"]
        saved = t.state.setdefault("snapshots", {}).get(str(step))
        if saved is None:
            t.state["snapshots"][str(step)] = {
                "id": identity,
                "next_seq": 0,
                "policy_step": step,
            }
        elif saved["id"] != identity:
            raise BudgetError("The policy snapshot identity changed.")
        save_json(t.state_path, t.state)
        t.active_step = step
        response = dict(result["response"])
        if keep:
            named = types.SaveWeightsForSamplerRequest(
                model_id=model_id,
                seq_id=seq["named"],
                path=f"{config.get('checkpoint_prefix', 'pilot-A')}-step-{step:02d}",
                ttl_seconds=config["checkpoint_ttl_seconds"],
            )
            saved = await self.operation(
                f"checkpoint-{step:02d}",
                named.model_dump(mode="json"),
                lambda: t.client.weights.save_for_sampler(request=named, max_retries=0),
                request_id=f"{model_id}:{seq['named']}",
                estimate=".02",
                maximum=".05",
                storage=True,
            )
            response["checkpoint"] = saved["response"]
        return response

    async def export(self, model_id, step, config):
        t = self.transport
        request = types.SaveWeightsExternalRequest(
            model_id=model_id,
            seq_id=3 * step + sum(k <= step for k in config["kept_checkpoints"]) + 1,
            path=f"{config.get('checkpoint_prefix', 'pilot-A')}-final-step-{step:02d}",
            ttl_seconds=config["checkpoint_ttl_seconds"],
        )
        result = await self.operation(
            "final-external",
            request.model_dump(mode="json"),
            lambda: t.client.weights.save_external(request=request, max_retries=0),
            request_id=f"{model_id}:{request.seq_id}",
            estimate=".02",
            maximum=".05",
            storage=True,
        )
        return result["response"]
