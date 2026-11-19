"""Skip tokenizer integration tests when their public assets are absent."""

import json
from pathlib import Path
import unittest

from huggingface_hub import try_to_load_from_cache

from scripts.download_test_tokenizers import REQUIRED_FILES
from twenty_bits.worlds import ROOT


def requires_tokenizer(model):
    manifest = json.loads((ROOT / "research/tokenizers.json").read_text())
    entry = next(row for row in manifest if row["model"] == model)
    directory = ROOT / entry["local_cache"]
    missing = []
    for name in REQUIRED_FILES:
        if directory.exists():
            present = (directory / name).is_file()
        else:
            cached = try_to_load_from_cache(model, name, revision=entry["revision"])
            present = isinstance(cached, str) and Path(cached).is_file()
        if not present:
            missing.append(name)
    return unittest.skipIf(
        bool(missing),
        f"Missing public tokenizer files for {model}: {', '.join(missing)} "
        f"in {entry['local_cache']} or the pinned Hugging Face cache. "
        "Download without credentials: python3 scripts/download_test_tokenizers.py",
    )
