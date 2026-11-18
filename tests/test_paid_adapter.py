"""Exercise real SDK serialization and fake requests; never contact Tinker."""

import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from contextlib import contextmanager

if any(
    importlib.util.find_spec(name) is None
    for name in ("tinker", "tinker_cookbook", "httpx")
):
    raise unittest.SkipTest(
        "Install .[paid] for SDK-adapter tests; all requests are mocked."
    )

import httpx
import tinker
from tinker._client import AsyncTinker
from tinker.lib.public_interfaces.sampling_client import SamplingClient
from tinker.lib.sdk_method import _entered

from twenty_bits.budget import CAP, BudgetError, Ledger
from twenty_bits.tinker_transport import GuardedTinker, sample_cost
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.worlds import ROOT


CONFIG = json.loads((ROOT / "evals/phase2.json").read_text())


class FakeResponse:
    def __init__(self, value):
        self.value = value

    async def json(self):
        return self.value


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        ledger_path = self.directory / "ledger.json"
        ledger_path.write_text(
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
        self.ledger = Ledger(ledger_path)
        self.transport = GuardedTinker(
            CONFIG, self.directory / "run", ledger=self.ledger
        )
        self.transport.usage_path = self.directory / "usage.jsonl"
        self.transport.state["samplers"][CONFIG["primary_model"]] = {
            "id": "sampler",
            "next_seq": 0,
        }
        self.submissions = 0
        self.polls = []
        self.outcomes = []

        async def submit(**kwargs):
            self.submissions += 1
            active = [
                e
                for e in self.ledger.status()["entries"]
                if "sample " in e["operation"]
            ]
            self.assertEqual(active[-1]["state"], "submitted")
            self.assertEqual(active[-1]["request_id"], "sampler:0")
            journal = json.loads(
                next((self.transport.directory / "requests").glob("*.json")).read_text()
            )
            self.assertEqual(journal["request_id"], "sampler:0")
            self.assertTrue(journal["request_id_saved_before_dispatch"])
            self.assertIn("saved_before_dispatch_at", journal)
            self.assertGreater(float(self.ledger.status()["held_usd"]), 0)
            self.assertEqual(kwargs["max_retries"], 0)
            return SimpleNamespace(
                model_dump=lambda **_: {"request_id": "sampler:0"},
                request_id="sampler:0",
            )

        async def retrieve(**kwargs):
            self.polls.append(kwargs["request"].request_id)
            value = self.outcomes.pop(0)
            if isinstance(value, Exception):
                raise value
            return FakeResponse(value)

        self.transport.client = SimpleNamespace(
            sampling=SimpleNamespace(asample=submit),
            futures=SimpleNamespace(
                with_raw_response=SimpleNamespace(retrieve=retrieve)
            ),
        )
        self.response = {
            "sequences": [
                {"tokens": [42, 43], "logprobs": [-1, -1], "stop_reason": "stop"}
            ],
            "prompt_cache_hit_tokens": 2,
        }

    async def sample(self):
        return await self.transport.sample(
            model=CONFIG["primary_model"],
            key="fake-game/turn-0",
            prompt=tinker.ModelInput.from_ints([1, 2, 3, 4]),
            params=tinker.SamplingParams(max_tokens=2048, seed=4),
        )

    async def test_408_and_try_again_poll_same_receipt_without_resubmitting(self):
        error = tinker.APIStatusError(
            "pending",
            response=httpx.Response(
                408, request=httpx.Request("POST", "https://fake.invalid")
            ),
            body={},
        )
        self.outcomes = [error, {"type": "try_again"}, self.response]
        with patch("twenty_bits.tinker_transport.asyncio.sleep", new=AsyncMock()):
            result = await self.sample()
        self.assertEqual(self.submissions, 1)
        self.assertEqual(self.polls, ["sampler:0"] * 3)
        self.assertEqual(result["prompt_cache_hit_tokens"], 2)
        self.assertEqual(self.ledger.status()["held_usd"], "0.000000")
        self.assertTrue(
            all(e["state"] == "settled" for e in self.ledger.status()["entries"])
        )
        await self.sample()
        self.assertEqual(self.submissions, 1)

    async def test_probe_prefix_keeps_write_ahead_ids_and_settlement(self):
        from twenty_bits.budget import money

        self.transport.run_cap = money("1.50")
        self.transport.operation_prefix = "[probe-test] "
        self.outcomes = [{"type": "try_again"}, self.response]
        with patch("twenty_bits.tinker_transport.asyncio.sleep", new=AsyncMock()):
            result = await self.sample()
        self.assertEqual(self.submissions, 1)
        self.assertEqual(self.polls, ["sampler:0", "sampler:0"])
        status = self.transport.run_status()
        self.assertEqual(money(status["spent_usd"]), money(result["actual_usd"]))
        self.assertEqual(money(status["held_usd"]), money("0"))

    async def test_reconnect_collects_pending_without_a_new_submission(self):
        self.outcomes = [RuntimeError("interrupted retrieval")]
        with self.assertRaises(RuntimeError):
            await self.sample()
        self.assertEqual(self.submissions, 1)
        self.outcomes = [self.response]
        await self.transport.collect_pending()
        await self.sample()
        self.assertEqual(self.submissions, 1)
        self.assertEqual(self.polls, ["sampler:0", "sampler:0"])

    async def test_failed_future_does_not_prevent_collecting_other_futures(self):
        self.outcomes = [RuntimeError("interrupted retrieval")]
        with self.assertRaises(RuntimeError):
            await self.sample()
        original = json.loads(
            next((self.transport.directory / "requests").glob("*.json")).read_text()
        )
        ledger_entry = self.ledger.reserve(
            phase=2,
            operation="second existing sample",
            estimate_usd=".001",
            max_cost_usd=".002",
        )
        self.ledger.dispatch(ledger_entry, lambda: None)
        self.ledger.attach_request_id(ledger_entry, "sampler:1")
        other = {
            **original,
            "entry_id": ledger_entry,
            "request_id": "sampler:1",
            "receipt": {"request_id": "sampler:1"},
            "key": "second-game",
        }
        from twenty_bits.tinker_transport import save_json

        save_json(self.transport.directory / "requests/other.json", other)

        async def poll(request_id):
            if request_id == "sampler:0":
                raise RuntimeError("expired")
            return self.response

        with patch.object(self.transport, "poll", new=poll):
            with self.assertRaises(RuntimeError):
                await self.transport.collect_pending()
        recovered = json.loads(
            (self.transport.directory / "requests/other.json").read_text()
        )
        self.assertTrue(recovered["settled"])
        self.assertFalse(
            json.loads(
                next(
                    p
                    for p in (self.transport.directory / "requests").glob("*.json")
                    if p.name != "other.json"
                ).read_text()
            ).get("settled", False)
        )

    async def test_network_failure_pauses_producers_and_retains_sample_hold(self):
        from twenty_bits.budget import money
        from twenty_bits.tinker_transport import NetworkInterruption

        self.transport.run_cap = money("1.5")
        self.transport.operation_prefix = "[probe-test] "
        self.outcomes = [
            tinker.APIConnectionError(
                request=httpx.Request("POST", "https://fake.invalid")
            )
        ]
        with self.assertRaises(NetworkInterruption):
            await self.sample()
        self.assertTrue(self.transport.failed)
        self.assertGreater(float(self.transport.run_status()["held_usd"]), 0)
        with self.assertRaises(BudgetError):
            await self.sample()
        self.assertEqual(self.submissions, 1)

    async def test_startup_recovers_pending_before_capability_requests(self):
        self.outcomes = [RuntimeError("interrupted retrieval")]
        with self.assertRaises(RuntimeError):
            await self.sample()
        self.outcomes = [self.response]

        async def capabilities():
            journal = json.loads(
                next((self.transport.directory / "requests").glob("*.json")).read_text()
            )
            self.assertTrue(journal["settled"])
            return {
                "supported_models": [
                    {"model_name": m, "sampleable": True}
                    for m in (CONFIG["primary_model"], CONFIG["reference_model"])
                ]
            }

        self.transport.client.service = SimpleNamespace(
            get_server_capabilities=capabilities
        )
        self.transport.state["session_id"] = "existing-session"
        with (
            patch("twenty_bits.tinker_transport.load_credentials"),
            patch(
                "twenty_bits.tinker_transport.AsyncTinker",
                return_value=self.transport.client,
            ),
        ):
            await self.transport.open(recover_pending=True)
        self.assertEqual(self.submissions, 1)

    async def test_interrupted_poll_retains_hold_and_resume_uses_saved_receipt(self):
        self.outcomes = [RuntimeError("interrupted retrieval")]
        with self.assertRaises(RuntimeError):
            await self.sample()
        held = self.ledger.status()["held_usd"]
        self.assertGreater(float(held), 0)
        self.outcomes = [self.response]
        await self.sample()
        self.assertEqual(self.submissions, 1)
        self.assertEqual(self.polls, ["sampler:0", "sampler:0"])
        self.assertEqual(self.ledger.status()["held_usd"], "0.000000")

    async def test_missing_receipt_recovers_saved_id_without_resubmission(self):
        self.transport.client.sampling.asample = AsyncMock(
            side_effect=ConnectionError("uncertain dispatch")
        )
        with self.assertRaises(ConnectionError):
            await self.sample()
        held = self.ledger.status()["held_usd"]
        self.transport.failed = False
        self.outcomes = [self.response]
        await self.sample()
        self.assertEqual(self.transport.client.sampling.asample.await_count, 1)
        self.assertGreater(float(held), 0)
        self.assertEqual(self.polls, ["sampler:0"])
        self.assertEqual(self.ledger.status()["held_usd"], "0.000000")

    async def test_resuming_changed_prompt_is_rejected(self):
        self.outcomes = [self.response]
        await self.sample()
        with self.assertRaises(RuntimeError):
            await self.transport.sample(
                model=CONFIG["primary_model"],
                key="fake-game/turn-0",
                prompt=tinker.ModelInput.from_ints([9]),
                params=tinker.SamplingParams(max_tokens=2048, seed=4),
            )

    async def test_unknown_usage_remains_held(self):
        self.outcomes = [{"sequences": self.response["sequences"]}]
        with self.assertRaises(ValueError):
            await self.sample()
        self.assertGreater(float(self.ledger.status()["held_usd"]), 0)

    async def test_orphaned_output_is_never_reused(self):
        self.outcomes = [self.response]
        await self.sample()
        path = next((self.transport.directory / "requests").glob("*.json"))
        journal = json.loads(path.read_text())
        journal["orphaned"] = True
        path.write_text(json.dumps(journal))
        with self.assertRaises(BudgetError):
            await self.sample()
        self.assertEqual(self.submissions, 1)

    async def test_sdk_serializes_submission_and_returns_raw_result(self):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            if request.url.path.endswith("asample"):
                return httpx.Response(200, json={"request_id": "wire-request"})
            return httpx.Response(200, json=self.response)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AsyncTinker(
            api_key="tml-dummy-test",
            base_url="https://fake.invalid",
            http_client=http,
            max_retries=0,
        )
        try:
            receipt = await client.sampling.asample(
                request=tinker.types.SampleRequest(
                    prompt=tinker.ModelInput.from_ints([1, 2]),
                    num_samples=1,
                    sampling_params=tinker.SamplingParams(max_tokens=2048, seed=3),
                    sampling_session_id="fake-sampler",
                    seq_id=0,
                ),
                max_retries=0,
            )
            response = await client.futures.with_raw_response.retrieve(
                request=tinker.types.FutureRetrieveRequest(
                    request_id=receipt.request_id
                ),
                max_retries=0,
            )
            self.assertEqual(await response.json(), self.response)
            self.assertEqual(seen[0]["sampling_params"]["max_tokens"], 2048)
            self.assertEqual(seen[0]["prompt"]["chunks"][0]["tokens"], [1, 2])
            self.assertEqual(seen[1]["request_id"], "wire-request")
        finally:
            await client.close()

    async def test_sampling_request_matches_high_level_sdk_wire_body_and_backpressure(
        self,
    ):
        seen = []

        def handler(request):
            seen.append((dict(request.headers), json.loads(request.content)))
            if request.url.path.endswith("asample"):
                return httpx.Response(200, json={"request_id": "sampler:0"})
            return httpx.Response(200, json=self.response)

        client = AsyncTinker(
            api_key="tml-dummy-test",
            base_url="https://fake.invalid",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            max_retries=0,
            default_headers={
                "x-sdk-version": tinker.__version__,
                "x-sdk-method": "TwentyBits.GuardedTinker",
            },
        )

        @contextmanager
        def aclient(_):
            yield client

        native = SamplingClient.__new__(SamplingClient)
        native.holder = SimpleNamespace(aclient=aclient)
        native._sampling_session_id = "sampler"
        native._record_stability_info = False
        params = tinker.SamplingParams(max_tokens=2048, seed=4)
        prompt = tinker.ModelInput.from_ints([1, 2, 3, 4])
        try:
            with _entered("SamplingClient.sample"):
                await native._send_asample_request(
                    0, 1, prompt, params, False, 0, 0, None, 0, None
                )
            self.transport.client = client
            await self.sample()
            self.assertEqual(seen[0][1], seen[1][1])
            self.assertEqual(seen[0][0]["x-tinker-sampling-backpressure"], "1")
            self.assertEqual(
                seen[0][0]["x-tinker-sampling-backpressure"],
                seen[1][0]["x-tinker-sampling-backpressure"],
            )
            self.assertEqual(seen[0][0]["x-sdk-version"], tinker.__version__)
        finally:
            await client.close()

    async def test_crash_after_settlement_uses_saved_response_without_new_request(self):
        self.outcomes = [self.response]
        await self.sample()
        path = next((self.transport.directory / "requests").glob("*.json"))
        journal = json.loads(path.read_text())
        del journal["settled"]
        path.write_text(json.dumps(journal))
        result = await self.sample()
        self.assertTrue(result["settled"])
        self.assertEqual(self.submissions, 1)
        self.assertEqual(len(self.polls), 1)

    async def test_receipt_mismatch_keeps_original_id_and_hold(self):
        self.transport.client.sampling.asample = AsyncMock(
            return_value=SimpleNamespace(
                request_id="unexpected",
                model_dump=lambda **_: {"request_id": "unexpected"},
            )
        )
        with self.assertRaises(BudgetError):
            await self.sample()
        sample = next(
            e
            for e in self.ledger.status()["entries"]
            if e["operation"].startswith("sample ")
        )
        self.assertEqual(sample["request_id"], "sampler:0")
        self.assertGreater(float(self.ledger.status()["held_usd"]), 0)

    async def test_validation_rejection_has_zero_cost_and_no_automatic_retry(self):
        error = tinker.APIStatusError(
            "outdated",
            response=httpx.Response(
                422, request=httpx.Request("POST", "https://fake.invalid")
            ),
            body={"detail": "outdated"},
        )
        self.transport.client.sampling.asample = AsyncMock(side_effect=error)
        with self.assertRaises(tinker.APIStatusError):
            await self.sample()
        self.assertEqual(self.ledger.status()["held_usd"], "0.000000")
        self.transport.failed = False
        with self.assertRaises(BudgetError):
            await self.sample()
        self.assertEqual(self.transport.client.sampling.asample.await_count, 1)


class UsageTests(unittest.TestCase):
    def test_cache_cost_matches_hand_calculation_and_rounds_up(self):
        self.assertEqual(sample_cost("Qwen/Qwen3-8B", 1000, 10, 800), "0.000077")
        self.assertEqual(sample_cost("Qwen/Qwen3-8B", 1000, 10, 0), "0.000201")
        with self.assertRaises(ValueError):
            sample_cost("Qwen/Qwen3-8B", 1000, 10, 1001)

    def test_qwen_native_action_spans(self):
        renderer = Rendering(CONFIG["primary_model"], CONFIG)
        tokens = (
            renderer.tokenizer.encode("ASK: has_fur", add_special_tokens=False)
            + renderer.renderer.get_stop_sequences()
        )
        decoded = renderer.decode(tokens)
        self.assertEqual(decoded["action"], "ASK: has_fur")
        self.assertEqual(decoded["reasoning_tokens"], 0)
        self.assertEqual(
            decoded["action_tokens"] + decoded["control_tokens"], len(tokens)
        )

    def test_reference_analysis_is_separate_from_action(self):
        renderer = Rendering(CONFIG["reference_model"], CONFIG)
        tokens = renderer.tokenizer.encode(
            "<|channel|>analysis<|message|>check the table<|end|><|start|>assistant<|channel|>final<|message|>ASK: has_fur",
            add_special_tokens=False,
        ) + [renderer.renderer.get_stop_sequences()[0]]
        decoded = renderer.decode(tokens)
        self.assertEqual(decoded["action"], "ASK: has_fur")
        self.assertGreater(decoded["reasoning_tokens"], 0)
        self.assertEqual(
            sum(
                decoded[k]
                for k in ["reasoning_tokens", "action_tokens", "control_tokens"]
            ),
            len(tokens),
        )

    def test_truncated_reference_analysis_has_no_action(self):
        renderer = Rendering(CONFIG["reference_model"], CONFIG)
        tokens = renderer.tokenizer.encode(
            "<|channel|>analysis<|message|>Need to inspect the table",
            add_special_tokens=False,
        )
        decoded = renderer.decode(tokens)
        self.assertEqual(decoded["action"], "")
        self.assertGreater(decoded["reasoning_tokens"], 0)
        self.assertEqual(decoded["parse_termination"], "malformed")

    def test_truncated_reference_final_keeps_complete_action(self):
        renderer = Rendering(CONFIG["reference_model"], CONFIG)
        tokens = renderer.tokenizer.encode(
            "<|channel|>final<|message|>ASK: has_fur", add_special_tokens=False
        )
        decoded = renderer.decode(tokens)
        self.assertEqual(decoded["action"], "ASK: has_fur")
        self.assertEqual(decoded["parse_termination"], "malformed")


if __name__ == "__main__":
    unittest.main()
