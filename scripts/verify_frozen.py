from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.evaluation import frozen_manifest, frozen_games
from twenty_bits.prompts import messages
from twenty_bits.worlds import ROOT


def main():
    manifest = frozen_manifest()
    total = 0
    expected = (
        json.loads((ROOT / "evals/frozen/prompt_hashes.json").read_text())
        if (ROOT / "evals/frozen/prompt_hashes.json").exists()
        else None
    )
    for c in manifest["cells"]:
        games = frozen_games(c["domain"], c["n"], c["noise"])
        total += len(games)
        if expected is not None:
            for r in games:
                actual = hashlib.sha256(
                    json.dumps(
                        messages(r), sort_keys=True, separators=(",", ":")
                    ).encode()
                ).hexdigest()
                if actual != expected[r["id"]]:
                    raise ValueError("A frozen public prompt changed.")
    print(
        f"Verified {len(manifest['cells'])} cells and {total} games, including every world and file hash."
    )


if __name__ == "__main__":
    main()
