import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    from twenty_bits.replacement_registry import refresh_legacy_ids
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "paid SDK extras are optional")
class ReplacementRegistryTests(unittest.TestCase):
    def test_serial_stages_keep_all_original_holds_and_current_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/"research";folder.mkdir()
            a=folder/"main_replacements.json";b=folder/"aux_replacements.json"
            a.write_text(json.dumps({"legacy_lost_entry_ids":["old"],"cases":[{"original_entry_id":"main-loss"}]}))
            current={"legacy_lost_entry_ids":["old"],"cases":[{"original_entry_id":"own-loss","replacement_key":"same"}]}
            b.write_text(json.dumps(current))
            with patch("twenty_bits.replacement_registry.ROOT",root):
                refresh_legacy_ids(b)
                once=b.read_bytes()
                refresh_legacy_ids(b)
            result=json.loads(b.read_text())
            self.assertEqual(result["legacy_lost_entry_ids"],["main-loss","old","own-loss"])
            self.assertEqual(result["cases"],current["cases"])
            self.assertEqual(b.read_bytes(),once)
