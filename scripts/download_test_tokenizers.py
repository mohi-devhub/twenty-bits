"""Download pinned public tokenizer assets for the integration tests."""

import json
from pathlib import Path
import sys

from huggingface_hub import snapshot_download

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


MODELS = ("Qwen/Qwen3-8B", "openai/gpt-oss-120b")
REQUIRED_FILES = ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja")
TOKENIZER_FILES = (
    *REQUIRED_FILES,
    "special_tokens_map.json",
    "added_tokens.json",
    "vocab.json",
    "merges.txt",
)


def main():
    manifest = json.loads((ROOT / "research/tokenizers.json").read_text())
    for model in MODELS:
        entry = next(row for row in manifest if row["model"] == model)
        directory = ROOT / entry["local_cache"]
        snapshot_download(
            repo_id=model,
            revision=entry["revision"],
            local_dir=directory,
            allow_patterns=list(TOKENIZER_FILES),
            token=False,
        )
        missing = [name for name in REQUIRED_FILES if not (directory / name).is_file()]
        if missing:
            raise FileNotFoundError(f"Incomplete tokenizer for {model}: {missing}")
        print(f"Ready: {model}@{entry['revision']} in {entry['local_cache']}")


if __name__ == "__main__":
    main()
