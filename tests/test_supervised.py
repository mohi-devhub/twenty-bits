"""Warm-start request recovery and native SDK serialization, with no service calls."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

if any(
    importlib.util.find_spec(name) is None
    for name in ("tinker", "tinker_cookbook", "httpx")
):
    raise unittest.SkipTest("Install .[paid] for mocked supervised-adapter tests.")

import httpx
import tinker
from tinker import types
from tinker._client import AsyncTinker
from tinker.proto.request_conv import forward_backward_request_to_proto
from twenty_bits.budget import CAP, BudgetError, Ledger
from twenty_bits.supervised import GuardedSupervised, supervised_data
from twenty_bits.tinker_transport import GuardedTinker, save_json
from twenty_bits.worlds import ROOT


class SupervisedRecoveryTests(unittest.IsolatedAsyncioTestCase):
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
        self.ledger = Ledger(path)
        self.transport = GuardedTinker(
            {"run_id": "sft-test"},
            directory / "run",
            ledger=self.ledger,
            usage_path=directory / "usage.jsonl",
            run_cap_usd="2.51",
        )
        self.trainer = GuardedSupervised(self.transport)
        self.sends = 0
        self.receipt = SimpleNamespace(
            request_id="training:1",
            model_dump=lambda **kw: {"request_id": "training:1"},
        )

    async def send(self):
        self.sends += 1
        path = self.transport.directory / "operations/test.json"
        journal = json.loads(path.read_text())
        self.assertIn("entry_id", journal)
        self.assertIn("saved_before_dispatch_at", journal)
        self.assertGreater(float(self.ledger.status()["held_usd"]), 0)
        return self.receipt

    async def test_pending_future_recovers_without_resubmitting(self):
        calls = 0

        async def poll(request_id):
            nonlocal calls
            calls += 1
            self.assertEqual(request_id, "training:1")
            if calls == 1:
                raise RuntimeError("interrupted collection")
            return {"ok": True}

        self.transport.poll = poll
        with self.assertRaises(RuntimeError):
            await self.trainer.operation(
                "test", {"tokens": 1}, self.send, estimate=".01", maximum=".01"
            )
        held = self.ledger.status()["held_usd"]
        result = await self.trainer.operation(
            "test", {"tokens": 1}, self.send, estimate=".01", maximum=".01"
        )
        self.assertTrue(result["settled"])
        self.assertEqual(self.sends, 1)
        self.assertGreater(float(held), 0)
        self.assertEqual(self.ledger.status()["held_usd"], "0.000000")

    async def test_missing_receipt_is_not_resubmitted(self):
        async def failed():
            self.sends += 1
            raise RuntimeError("lost receipt")

        with self.assertRaises(RuntimeError):
            await self.trainer.operation(
                "test", {}, failed, estimate=".01", maximum=".01"
            )
        with self.assertRaises(BudgetError):
            await self.trainer.operation(
                "test", {}, failed, estimate=".01", maximum=".01"
            )
        self.assertEqual(self.sends, 1)
        self.assertGreater(float(self.ledger.status()["held_usd"]), 0)

    async def test_storage_hold_is_retained_after_result_collection(self):
        async def poll(_):
            return {"path": "tinker://unit/sampler_weights/test"}

        self.transport.poll = poll
        result = await self.trainer.operation(
            "test", {}, self.send, estimate=".02", maximum=".05", storage=True
        )
        self.assertTrue(result["completed"])
        self.assertNotIn("settled", result)
        await self.trainer.operation(
            "test", {}, self.send, estimate=".02", maximum=".05", storage=True
        )
        self.assertEqual(self.sends, 1)
        self.assertEqual(self.ledger.status()["held_usd"], "0.050000")

    async def test_saved_response_after_crash_is_settled_without_polling(self):
        async def poll(_):
            return {"ok": True}

        self.transport.poll = poll
        result = await self.trainer.operation(
            "test", {}, self.send, estimate=".01", maximum=".01"
        )
        path = self.transport.directory / "operations/test.json"
        result.pop("settled")
        save_json(path, result)

        async def forbidden(_):
            raise AssertionError("A saved response must not be retrieved again")

        self.transport.poll = forbidden
        recovered = await self.trainer.operation(
            "test", {}, self.send, estimate=".01", maximum=".01"
        )
        self.assertTrue(recovered["settled"])
        self.assertEqual(self.sends, 1)


class NativeTrainingWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_sdk_training_wire_matches_declared_payload(self):
        datum = types.Datum(
            model_input=tinker.ModelInput.from_ints([10, 20]),
            loss_fn_inputs={
                "target_tokens": tinker.TensorData(
                    data=[20, 30], dtype="int64", shape=[2]
                ),
                "weights": tinker.TensorData(
                    data=[0.0, 1.0], dtype="float32", shape=[2]
                ),
            },
        )
        forward = types.ForwardBackwardRequest(
            model_id="unit:train:0",
            seq_id=1,
            forward_backward_input=types.ForwardBackwardInput(
                data=[datum], loss_fn="cross_entropy"
            ),
        )
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={"request_id": "unit-future"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            client = AsyncTinker(
                api_key="tml-unit-key",
                base_url="https://unit.invalid",
                http_client=http,
                max_retries=0,
            )
            await client.models.create(
                request=types.CreateModelRequest(
                    session_id="unit",
                    model_seq_id=0,
                    base_model="Qwen/Qwen3-8B",
                    lora_config=types.LoraConfig(rank=32, seed=11),
                )
            )
            await client.training.forward_backward(request=forward)
            await client.training.optim_step(
                request=types.OptimStepRequest(
                    model_id="unit:train:0",
                    seq_id=2,
                    optim_params=types.AdamParams(learning_rate=1e-4),
                )
            )
        self.assertEqual(json.loads(requests[0].content)["lora_config"]["rank"], 32)
        body = requests[1].content
        if requests[1].headers.get("content-encoding") == "zstd":
            import zstandard

            body = zstandard.ZstdDecompressor().decompress(body)
        self.assertEqual(
            body, forward_backward_request_to_proto(forward).SerializeToString()
        )
        optim = json.loads(requests[2].content)
        self.assertEqual(optim["seq_id"], 2)
        self.assertEqual(optim["adam_params"]["learning_rate"], 1e-4)


class SupervisionTests(unittest.TestCase):
    def test_approved_examples_have_no_trainable_prompt_tokens(self):
        config = json.loads((ROOT / "experiments/alias_probe.json").read_text())
        price = json.loads((ROOT / "research/format_warmstart_price.json").read_text())
        config.update(
            training_data="experiments/format_warmstart_proposal.jsonl.gz",
            training_data_sha256=price["data_sha256"],
            examples=price["examples"],
            tokens_per_epoch=price["full_context_tokens_per_epoch"],
        )
        data = supervised_data(config)
        self.assertEqual(len(data), 554)
        self.assertEqual(sum(d.model_input.length for d in data), 413627)


if __name__ == "__main__":
    unittest.main()
