"""Render the deterministic HTML timelines locally and encode shareable GIFs."""

from pathlib import Path
import argparse
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-mp4", action="store_true")
    args = parser.parse_args()
    env = {**os.environ, "npm_config_script_shell": "/bin/sh"}
    exports = []
    for label in ["noiseless", "noisy"]:
        directory = ROOT / "replays"
        mp4 = directory / f"baseline-{label}.mp4"
        gif = directory / f"baseline-{label}.gif"
        if not args.reuse_mp4:
            subprocess.run(
                [
                    "npx",
                    "--yes",
                    "hyperframes@0.9.63",
                    "render",
                    "-c",
                    f"compositions/{label}.html",
                    "-o",
                    mp4.name,
                    "--fps",
                    "12",
                    "--quality",
                    "standard",
                ],
                cwd=directory,
                env=env,
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
                "fps=6,scale=1000:-1:flags=lanczos,split[x][y];[x]palettegen[p];[y][p]paletteuse",
                "-loop",
                "0",
                str(gif),
            ],
            check=True,
        )
        probe = subprocess.run(
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
            capture_output=True,
            text=True,
            check=True,
        )
        metadata = json.loads(probe.stdout)
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        exports.append(
            {
                "label": label,
                "mp4": str(mp4.relative_to(ROOT)),
                "gif": str(gif.relative_to(ROOT)),
                "duration_seconds": float(metadata["format"]["duration"]),
                "width": video["width"],
                "height": video["height"],
                "frames": int(video["nb_frames"]),
            }
        )
    (ROOT / "replays/exports.json").write_text(json.dumps(exports, indent=2) + "\n")
    print(json.dumps(exports, indent=2))


if __name__ == "__main__":
    main()
