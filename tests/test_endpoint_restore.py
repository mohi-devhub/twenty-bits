import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from twenty_bits.budget import BudgetError
from twenty_bits.endpoint_restore import restore_A11_endpoint


class EndpointReuseTests(unittest.IsolatedAsyncioTestCase):
    async def setup_case(self, root):
        sampler = "unit:sample:30"
        model = "unit:train:0"
        completion = root / "results/main_A11/completion.json"
        completion.parent.mkdir(parents=True)
        completion.write_text(
            json.dumps(
                {
                    "training_model_id": model,
                    "snapshots": {"30": {"id": sampler, "next_seq": 10}},
                }
            )
        )
        adapter = root / "runs/main-U-A11-v1/adapter/adapter_model.safetensors"
        adapter.parent.mkdir(parents=True)
        adapter.write_bytes(b"unit adapter")
        expected = {
            "bytes": len(adapter.read_bytes()),
            "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        }
        info = {
            "sampler_id": sampler,
            "base_model": "model",
            "model_path": "tinker://" + model + "/sampler_weights/~ephemeral_90",
        }

        async def free(name, send):
            return info

        transport = SimpleNamespace(
            free=free,
            state={},
            state_path=root / "state.json",
            ledger=SimpleNamespace(
                status=lambda: {
                    "entries": [
                        {"request_id": sampler + ":11"},
                        {"request_id": "other:90"},
                    ]
                }
            ),
        )
        config = {
            "is_primary_result": False,
            "rl_training_authorized": False,
            "primary_model": "model",
            "source_adapter_files": {adapter.name: expected},
        }
        return transport, config, info

    async def test_new_ids_follow_all_existing_ledger_ids_without_training(self):
        with (
            TemporaryDirectory() as temp,
            patch("twenty_bits.endpoint_restore.ROOT", Path(temp)),
        ):
            transport, config, _ = await self.setup_case(Path(temp))
            result = await restore_A11_endpoint(transport, config)
            self.assertEqual(transport.state["snapshots"]["30"]["next_seq"], 12)
            self.assertFalse(result["weights_reloaded_or_trained"])
            await restore_A11_endpoint(transport, config)
            self.assertEqual(transport.active_step, 30)

    async def test_stale_counter_and_wrong_endpoint_are_rejected(self):
        with (
            TemporaryDirectory() as temp,
            patch("twenty_bits.endpoint_restore.ROOT", Path(temp)),
        ):
            transport, config, info = await self.setup_case(Path(temp))
            transport.state["snapshots"] = {
                "30": {"id": info["sampler_id"], "next_seq": 11}
            }
            with self.assertRaises(BudgetError):
                await restore_A11_endpoint(transport, config)
            transport.state.clear()
            info["base_model"] = "another"
            with self.assertRaises(BudgetError):
                await restore_A11_endpoint(transport, config)

    async def test_primary_and_training_configs_cannot_use_the_helper(self):
        for field in ("is_primary_result", "rl_training_authorized"):
            with TemporaryDirectory() as temp:
                transport, config, _ = await self.setup_case(Path(temp))
                config[field] = True
                with self.assertRaises(BudgetError):
                    await restore_A11_endpoint(transport, config)

    async def test_finished_source_is_rejected_before_metadata_or_sampling(self):
        with (
            TemporaryDirectory() as temp,
            patch("twenty_bits.endpoint_restore.ROOT", Path(temp)),
        ):
            transport, config, _ = await self.setup_case(Path(temp))
            path = Path(temp) / "runs/main-U-A11-v1/sessions.json"
            path.write_text(json.dumps({"finished": True}))

            async def forbidden(*args):
                raise AssertionError(
                    "Metadata must not be mistaken for usable weights."
                )

            transport.free = forbidden
            with self.assertRaises(BudgetError):
                await restore_A11_endpoint(transport, config)
