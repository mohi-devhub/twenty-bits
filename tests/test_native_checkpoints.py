import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

try:
    from twenty_bits.native_checkpoints import require_checkpoint, save_native, storage_estimate
    from twenty_bits.budget import BudgetError
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "paid SDK extras are optional")
class NativeCheckpointTests(unittest.TestCase):
    def test_paid_storage_bound(self):
        self.assertEqual(storage_estimate(1_000_000_000), Decimal("0.10"))

    def test_persistent_checkpoint_needs_nonzero_size(self):
        with self.assertRaises(BudgetError):
            require_checkpoint({"checkpoint_type": "sampler", "size_bytes": 0,
                                "tinker_path": "tinker://own/sampler_weights/end"}, "own", "sampler")

    def test_expiring_or_other_owner_checkpoint_rejected(self):
        valid = {"checkpoint_type": "sampler", "size_bytes": 100,
                 "tinker_path": "tinker://own/sampler_weights/end", "expires_at": None}
        self.assertEqual(require_checkpoint(valid, "own", "sampler"), valid)
        for row in ({**valid, "expires_at": "tomorrow"},
                    {**valid, "tinker_path": "tinker://other/sampler_weights/end"}):
            with self.assertRaises(BudgetError):
                require_checkpoint(row, "own", "sampler")


@unittest.skipUnless(AVAILABLE, "paid SDK extras are optional")
class NativeSaveTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_native_save_types_have_no_expiry_and_saved_id(self):
        from pathlib import Path
        import tempfile
        for kind, segment in (("training", "weights"), ("sampler", "sampler_weights")):
            with tempfile.TemporaryDirectory() as directory:
                path = f"tinker://own/{segment}/end"
                row = {"tinker_path": path, "checkpoint_type": kind,
                       "size_bytes": 100, "expires_at": None}
                client = SimpleNamespace(weights=SimpleNamespace(save=AsyncMock(), save_for_sampler=AsyncMock(), list=Mock()))
                async def free(operation, send):
                    send()
                    return {"checkpoints": [row]}
                t = SimpleNamespace(client=client, directory=Path(directory), free=free,
                                    ledger=SimpleNamespace(_update=Mock()))
                async def operation(key, payload, send, **kwargs):
                    self.assertIsNone(payload["ttl_seconds"])
                    self.assertEqual(kwargs["request_id"], "own:91")
                    self.assertTrue(kwargs["storage"])
                    await send()
                    return {"response": {"path": path}, "entry_id": "reserved"}
                trainer = SimpleNamespace(transport=t, operation=operation)
                saved = await save_native(trainer, "own", name="end", seq=91,
                                          kind=kind, estimate=".1", maximum=".15")
                self.assertEqual(saved["tinker_path"], path)
                method = client.weights.save if kind == "training" else client.weights.save_for_sampler
                method.assert_awaited_once()
                self.assertIsNone(method.call_args.kwargs["request"].ttl_seconds)
