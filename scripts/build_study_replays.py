"""Reuse the replay viewer for rule-selected saved-game contrasts."""

import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.attributes import attribute_code
from twenty_bits.worlds import ROOT


def main():
    folder = ROOT / "replays/study"
    examples = json.loads((folder / "games.json").read_text())
    for example in examples:
        example["attribute_codes"] = {
            attribute_code(i): name
            for i, name in enumerate(example["record"]["world"]["attributes"])
        }
    (folder / "games.json").write_text(json.dumps(examples, indent=2) + "\n")
    (folder / "games.js").write_text(
        "window.REPLAYS = " + json.dumps(examples, separators=(",", ":")) + ";\n"
    )
    template = (ROOT / "replays/index.html").read_text()
    (folder / "assets").mkdir(exist_ok=True)
    (folder / "compositions").mkdir(exist_ok=True)
    (folder / "viewer").mkdir(exist_ok=True)
    for source in (ROOT / "replays/assets").iterdir():
        if source.is_file():
            shutil.copyfile(source, folder / "assets" / source.name)
    for name in ("replay.js", "replay.css", "hyperframes.json", "package.json"):
        shutil.copyfile(ROOT / "replays" / name, folder / name)
    compositions = []
    for index, example in enumerate(examples):
        duration = 2 * (max(len(p["trace"]["turns"]) for p in example["players"]) + 1)
        html = (
            template.replace('href="replay.css"', 'href="../replay.css"')
            .replace('src="assets/gsap.min.js"', 'src="../assets/gsap.min.js"')
            .replace('src="replay.js"', 'src="../replay.js"')
            .replace('src="games.js"', 'src="../games.js"')
        )
        html = html.replace('data-duration="22"', f'data-duration="{duration}"')
        html = html.replace(
            "<title>Twenty Bits — Search, side by side</title>",
            f"<title>Twenty Bits: {example['label']}</title>",
        )
        html = html.replace("Offline baselines", "Saved model games")
        html = html.replace(
            "Same target.<br /><em>Different questions.</em>",
            "Same target.<em>Different failures.</em>"
            if index == 0
            else "Same weights.<em>Visible budget.</em>",
        )
        html = html.replace(
            "Watch each answer reshape the<br />space of possible candidates.",
            "Candidate state is supplied to every policy. Viewer metrics below are not model observations.",
        )
        html = html.replace(
            "Real baseline logs · Same target and noise schedule · Illustrative\n            game selection",
            "Saved frozen-game logs · Rule-selected contrast · No new model calls",
        )
        html = html.replace(
            '<option value="0">Truthful answers</option>',
            '<option value="0">Gamble and stall</option>',
        ).replace(
            '<option value="1">10% noisy answers</option>',
            '<option value="1">Visible-budget follow-up</option>',
        )
        html = html.replace(
            '<div class="surprise"></div>',
            '<div class="action-meaning"></div><div class="surprise"></div><div class="prompt-budget"></div>',
        )
        html = html.replace("Questions asked", "Questions used (viewer)")
        settings = f"<script>window.REPLAY_STUDY = true; window.REPLAY_EXAMPLE = {index}; window.REPLAY_EXPORT = true;</script>"
        html = html.replace(
            '<script src="../replay.js"></script>',
            settings + '\n<script src="../replay.js"></script>',
        )
        html = html.replace(
            "</head>", '<link rel="stylesheet" href="../study.css" />\n</head>'
        ).replace("<body>", '<body class="study">')
        (folder / "compositions" / f"{example['id']}.html").write_text(html)
        compositions.append(html)
        old = folder / f"{example['id']}.html"
        if old.exists():
            old.unlink()
    interactive = compositions[0].replace(
        "window.REPLAY_EXPORT = true;", "window.REPLAY_EXPORT = false;"
    )
    (folder / "viewer/index.html").write_text(interactive)
    (folder / "index.html").write_text(compositions[0].replace('"../', '"'))
    print([(e["id"], e["record"]["id"]) for e in examples])


if __name__ == "__main__":
    main()
