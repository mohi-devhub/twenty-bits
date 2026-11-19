"""Render the saved-game compositions locally; no model or service client."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-mp4", action="store_true")
    args = parser.parse_args()
    folder = ROOT / "replays/study"
    environment = {**os.environ, "npm_config_script_shell": "/bin/sh"}
    exports = []
    for name in ("gamble-stall", "budget-fix"):
        mp4, gif = folder / f"{name}.mp4", folder / f"{name}.gif"
        if not args.reuse_mp4:
            subprocess.run(
                [
                    "npx",
                    "--yes",
                    "hyperframes@0.9.63",
                    "render",
                    "-c",
                    f"compositions/{name}.html",
                    "-o",
                    mp4.name,
                    "--fps",
                    "12",
                    "--quality",
                    "delivery",
                    "--strict",
                ],
                cwd=folder,
                env=environment,
                check=True,
            )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(mp4),
                "-filter_complex",
                "fps=6,scale=1400:-1:flags=lanczos,split[x][y];[x]palettegen[p];[y][p]paletteuse",
                "-loop",
                "0",
                str(gif),
            ],
            check=True,
        )
        metadata = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_streams",
                    "-show_format",
                    "-of",
                    "json",
                    str(mp4),
                ],
                text=True,
            )
        )
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        exports.append(
            {
                "name": name,
                "mp4": str(mp4.relative_to(ROOT)),
                "gif": str(gif.relative_to(ROOT)),
                "duration_seconds": float(metadata["format"]["duration"]),
                "width": video["width"],
                "height": video["height"],
                "frames": int(video["nb_frames"]),
                "fps": video["avg_frame_rate"],
                "renderer": "hyperframes@0.9.63",
                "source": f"replays/study/compositions/{name}.html",
                "new_model_calls": 0,
            }
        )
    (folder / "exports.json").write_text(json.dumps(exports, indent=2) + "\n")
    print(json.dumps(exports, indent=2))


if __name__ == "__main__":
    main()
