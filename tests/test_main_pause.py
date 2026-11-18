"""An explicit pause must prevent even SDK initialization."""

import asyncio
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

if importlib.util.find_spec("tinker") is None:
    raise unittest.SkipTest("Install .[paid] for mocked pause checks.")

from scripts import run_main_seed


class MainPauseTests(unittest.TestCase):
    def test_pause_returns_before_config_credentials_or_service_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "research").mkdir()
            (root / "research/main_A11_pause.json").write_text(
                json.dumps({"active": True})
            )
            with (
                patch.object(run_main_seed, "ROOT", root),
                patch.object(
                    run_main_seed.PilotTransport,
                    "open",
                    side_effect=AssertionError("No service access"),
                ) as opened,
                redirect_stdout(io.StringIO()),
            ):
                asyncio.run(run_main_seed.main())
            opened.assert_not_called()
            self.assertFalse((root / "ledger.json").exists())


if __name__ == "__main__":
    unittest.main()
