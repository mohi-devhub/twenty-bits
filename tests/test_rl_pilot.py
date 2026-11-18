"""RL return math, cookbook loss masks and durable mutation recovery offline."""

import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

if any(
    importlib.util.find_spec(n) is None
    for n in ("tinker", "tinker_cookbook", "torch", "httpx")
):
    raise unittest.SkipTest("Install .[paid] for mocked RL checks.")

import httpx
import numpy as np
import tinker
from tinker import types
from tinker._client import AsyncTinker
from tinker.proto.request_conv import forward_backward_request_to_proto
from tinker_cookbook.completers import TokensWithLogprobs
from tinker_cookbook.rl.types import Trajectory, Transition
from twenty_bits.budget import CAP, BudgetError, Ledger
from twenty_bits.rl_pilot import (
    GuardedRL,
    PilotTransport,
    SamplingScope,
    group_data,
    pack_trajectory,
    sequence_ids,
    standardized_advantages,
    unpack_trajectory,
)


class GroupMathTests(unittest.TestCase):
    def test_standardization_uses_population_std(self):
        actual = standardized_advantages([0, 0, 0, 0, 1, 1, 1, 1])
        np.testing.assert_allclose(actual, [-1] * 4 + [1] * 4, atol=3e-8)
        self.assertAlmostEqual(actual.mean(), 0)

    def test_constant_and_numerically_constant_returns_give_zero(self):
        for values in ([0.91] * 8, [0.91] * 4 + [0.9100000000000001] * 4):
            np.testing.assert_array_equal(standardized_advantages(values), np.zeros(8))

    def test_wrong_group_or_nonfinite_return_is_rejected(self):
        for values in ([1] * 4, [float("nan")] * 8):
            with self.assertRaises(ValueError):
                standardized_advantages(values)

    def test_every_sampled_token_trains_once_and_environment_tokens_never_train(self):
        trajectories = []
        for i in range(8):
            rows = [
                Transition(
                    ob=tinker.ModelInput.from_ints([10, 20]),
                    ac=TokensWithLogprobs(
                        tokens=[30, 31], maybe_logprobs=[-0.1, -0.2], stop_reason="stop"
                    ),
                    reward=-0.03,
                    episode_done=False,
                    metrics={"eig": 1000},
                ),
                Transition(
                    ob=tinker.ModelInput.from_ints([10, 20, 30, 31, 40, 41]),
                    ac=TokensWithLogprobs(
                        tokens=[50], maybe_logprobs=[-0.3], stop_reason="stop"
                    ),
                    reward=float(i < 4),
                    episode_done=True,
                    metrics={"eig": -1000},
                ),
            ]
            trajectories.append(
                Trajectory(transitions=rows, final_ob=tinker.ModelInput.empty())
            )
        data, archive, returns, advantages = group_data(trajectories)
        np.testing.assert_allclose(returns, [0.97] * 4 + [-0.03] * 4)
        np.testing.assert_allclose(advantages, [1] * 4 + [-1] * 4, atol=3e-8)
        self.assertEqual(sum(sum(r["training_mask"]) for r in archive), 24)
        self.assertEqual(len(data), 8)
        self.assertEqual(data[0].model_input.to_ints(), [10, 20, 30, 31, 40, 41])
        self.assertEqual(data[0].loss_fn_inputs["advantages"].data[3:5], [0, 0])
        self.assertNotIn("mask", data[0].loss_fn_inputs)
        self.assertEqual(
            pack_trajectory(unpack_trajectory(pack_trajectory(trajectories[0]))),
            pack_trajectory(trajectories[0]),
        )

    def test_snapshot_and_training_sequence_ids_are_contiguous(self):
        seen = []
        for step in range(1, 17):
            ids = sequence_ids(step, [4, 8, 12, 16])
            seen.extend(v for v in ids.values() if v is not None)
        self.assertEqual(seen, list(range(1, 53)))


class DurableRLTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        path = directory / "ledger.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cap_usd": str(CAP),
                    "reservation_multiplier": "1.5",
                    "entries": [],
                    "blocks": [],
                }
            )
        )
        self.transport = PilotTransport(
            {"run_id": "rl-unit", "ledger_phase": 3, "primary_model": "Qwen/Qwen3-8B"},
            directory / "run",
            ledger=Ledger(path),
            usage_path=directory / "usage.jsonl",
            run_cap_usd=".10",
        )
        self.trainer = GuardedRL(self.transport)
        self.sends = 0

    async def send(self):
        self.sends += 1
        journal = json.loads(
            (self.transport.directory / "operations/test.json").read_text()
        )
        entry = self.transport.ledger.status()["entries"][0]
        self.assertEqual(entry["request_id"], journal["request_id"])
        self.assertTrue(journal["request_id_saved_before_dispatch"])
        self.assertEqual(entry["phase"], 3)
        self.assertGreater(float(entry["reserved_usd"]), 0)
        return SimpleNamespace(
            request_id="unit:train:0:1",
            model_dump=lambda **kw: {"request_id": "unit:train:0:1"},
        )

    async def test_lost_receipt_recovers_saved_id_without_resubmission(self):
        async def lost():
            await self.send()
            raise tinker.APIConnectionError(
                request=httpx.Request("POST", "https://unit.invalid")
            )

        with self.assertRaises(BudgetError):
            await self.trainer.operation(
                "test",
                {},
                lost,
                request_id="unit:train:0:1",
                estimate=".01",
                maximum=".01",
            )
        self.assertGreater(float(self.transport.ledger.status()["held_usd"]), 0)

        async def poll(request_id):
            self.assertEqual(request_id, "unit:train:0:1")
            return {"ok": True}

        self.transport.poll = poll
        await self.trainer.recover()
        result = await self.trainer.operation(
            "test", {}, lost, request_id="unit:train:0:1", estimate=".01", maximum=".01"
        )
        self.assertTrue(result["settled"])
        self.assertEqual(self.sends, 1)
        self.assertEqual(self.transport.ledger.status()["spent_usd"], "0.010000")

    async def test_pending_collection_keeps_original_hold_and_same_request(self):
        polls = 0

        async def poll(request_id):
            nonlocal polls
            polls += 1
            self.assertEqual(request_id, "unit:train:0:1")
            if polls == 1:
                raise RuntimeError("connection dropped while polling")
            return {"ok": True}

        self.transport.poll = poll
        with self.assertRaises(RuntimeError):
            await self.trainer.operation(
                "test",
                {},
                self.send,
                request_id="unit:train:0:1",
                estimate=".01",
                maximum=".01",
            )
        result = await self.trainer.operation(
            "test",
            {},
            self.send,
            request_id="unit:train:0:1",
            estimate=".01",
            maximum=".01",
        )
        self.assertTrue(result["settled"])
        self.assertEqual(self.sends, 1)

    async def test_storage_hold_remains_after_result_is_collected(self):
        async def poll(_):
            return {"path": "tinker://unit/sampler_weights/a"}

        self.transport.poll = poll
        await self.trainer.operation(
            "test",
            {},
            self.send,
            request_id="unit:train:0:1",
            estimate=".02",
            maximum=".05",
            storage=True,
        )
        self.assertEqual(self.transport.ledger.status()["held_usd"], "0.050000")
        await self.trainer.recover()
        self.assertEqual(self.sends, 1)

    async def test_changed_payload_and_run_cap_refuse_before_dispatch(self):
        async def poll(_):
            return {"ok": True}

        self.transport.poll = poll
        await self.trainer.operation(
            "test",
            {},
            self.send,
            request_id="unit:train:0:1",
            estimate=".01",
            maximum=".01",
        )
        with self.assertRaises(BudgetError):
            await self.trainer.operation(
                "test",
                {"changed": True},
                self.send,
                request_id="unit:train:0:1",
                estimate=".01",
                maximum=".01",
            )
        with self.assertRaises(BudgetError):
            await self.trainer.operation(
                "too-much",
                {},
                self.send,
                request_id="unit:train:0:2",
                estimate=".10",
                maximum=".10",
            )
        self.assertEqual(self.sends, 1)

    async def test_snapshot_counters_survive_selection_and_restart(self):
        self.transport.state["snapshots"] = {
            "0": {"id": "base", "next_seq": 5},
            "1": {"id": "trained", "next_seq": 7},
        }
        self.transport.active_step = 0
        (await self.transport.sampler("Qwen/Qwen3-8B"))["next_seq"] += 1
        from twenty_bits.tinker_transport import save_json

        save_json(self.transport.state_path, self.transport.state)
        other = PilotTransport(
            self.transport.config,
            self.transport.directory,
            ledger=self.transport.ledger,
            usage_path=self.transport.usage_path,
            run_cap_usd=".10",
        )
        other.active_step = 1
        self.assertEqual((await other.sampler("Qwen/Qwen3-8B"))["next_seq"], 7)
        other.active_step = 0
        self.assertEqual((await other.sampler("Qwen/Qwen3-8B"))["next_seq"], 6)

    async def test_group_scopes_do_not_reuse_another_members_key(self):
        keys = []

        async def sample(**kw):
            keys.append(kw["key"])

        target = SimpleNamespace(sample=sample)
        await asyncio.gather(
            *(
                SamplingScope(target, f"member-{i}/").sample(key="same-world/turn-0")
                for i in range(8)
            )
        )
        self.assertEqual(len(set(keys)), 8)

    async def test_importance_sampling_wire_uses_exact_cookbook_arrays(self):
        datum = types.Datum(
            model_input=tinker.ModelInput.from_ints([10, 20]),
            loss_fn_inputs={
                "target_tokens": [20, 30],
                "logprobs": [0, -0.5],
                "advantages": [0, 1],
            },
        )
        request = types.ForwardBackwardRequest(
            model_id="unit:train:0",
            seq_id=1,
            forward_backward_input=types.ForwardBackwardInput(
                data=[datum], loss_fn="importance_sampling"
            ),
        )
        sent = []

        def respond(req):
            sent.append(req)
            return httpx.Response(200, json={"request_id": "unit:train:0:1"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            client = AsyncTinker(
                api_key="tml-unit-key",
                base_url="https://unit.invalid",
                http_client=http,
                max_retries=0,
            )
            await client.training.forward_backward(request=request)
        body = sent[0].content
        if sent[0].headers.get("content-encoding") == "zstd":
            import zstandard

            body = zstandard.ZstdDecompressor().decompress(body)
        self.assertEqual(
            body, forward_backward_request_to_proto(request).SerializeToString()
        )

    async def test_production_update_uses_supported_sdk_signatures(self):
        datum = types.Datum(
            model_input=tinker.ModelInput.from_ints([10, 20]),
            loss_fn_inputs={
                "target_tokens": [20, 30],
                "logprobs": [0, -0.3],
                "advantages": [0, 1],
            },
        )
        archive = [
            {
                "input_tokens": [10, 20],
                "loss_fn_inputs": {
                    k: {"data": v.data, "dtype": v.dtype, "shape": v.shape}
                    for k, v in datum.loss_fn_inputs.items()
                },
                "training_mask": [0, 1],
                "metadata": {"group_idx": 0, "traj_idx": 0},
            }
        ]
        requests = []

        def respond(req):
            requests.append(req)
            return httpx.Response(
                200, json={"request_id": f"unit:train:0:{len(requests)}"}
            )

        async def poll(_):
            return {
                "loss_fn_outputs": [{"logprobs": {"data": [-0.1, -0.2]}}],
                "metrics": {},
            }

        self.transport.poll = poll
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            self.transport.client = AsyncTinker(
                api_key="tml-unit-key",
                base_url="https://unit.invalid",
                http_client=http,
                max_retries=0,
            )
            result = await self.trainer.update(
                "unit:train:0",
                1,
                [datum],
                archive,
                {
                    "primary_model": "Qwen/Qwen3-8B",
                    "kept_checkpoints": [4, 8, 12, 16],
                    "adam": {
                        "learning_rate": 4e-5,
                        "beta1": 0.9,
                        "beta2": 0.95,
                        "eps": 1e-8,
                    },
                },
            )
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["training_tokens"], 2)
        self.assertEqual(json.loads(requests[1].content)["seq_id"], 2)


if __name__ == "__main__":
    unittest.main()
