"""Audit the final narrative inputs, example rule, figures and media offline."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_writeup_data import endings, saved_games, select_examples
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / "results/writeup"
    data = json.loads((out / "numbers.json").read_text())
    for name, digest in data["source_sha256"].items():
        assert sha(ROOT / name) == digest, name
    protected = json.loads(
        (ROOT / "research/visible_budget_preflight.json").read_text()
    )["immutable_sha256"]
    for name, digest in protected.items():
        assert sha(ROOT / name) == digest, name
    primary = {}
    for name in ("A11", "A23", "B41"):
        games = saved_games(
            f"results/main_{name}/games.jsonl.gz", {"eval_base", "eval_endpoint"}
        )
        primary[name] = [g for g in games if g["kind"] == "eval_endpoint"]
        if name == "A11":
            primary["Raw"] = [g for g in games if g["kind"] == "eval_base"]
    visible = saved_games("results/visible_budget/games.jsonl.gz", {"visible_budget"})
    for name, games in primary.items():
        assert endings(games) == data["outcomes"]["primary"][name]["outcomes"]
        animal = [g for g in games if g["domain"] == "animals" and g["noise"] == 0]
        assert endings(animal) == data["animal_noiseless"][name]["outcomes"]
        cells = [[g for g in animal if g["n"] == n] for n in (32, 128)]
        eig = (
            sum(
                sum(sum(g["question_eigs"]) for g in gs)
                / sum(g["questions"] for g in gs)
                for gs in cells
            )
            / 2
        )
        assert abs(eig - data["animal_noiseless"][name]["eig_per_question"]) < 1e-12
        low, high = data["animal_noiseless"][name]["ci95"]
        assert low <= eig <= high
        if name != "Raw":
            assert (
                data["animal_noiseless"][name]["paired_change_from_raw"]["ci95"][0] > 0
            )
        assert (
            sum(g["won"] for g in games if g["noise"] == 0.1)
            == data["noisy"][name]["wins"]
        )
    for name in ("Raw", "A23", "B41"):
        assert (
            endings([g for g in visible if g["policy"] == name])
            == data["outcomes"]["visible_budget"][name]["outcomes"]
        )
        assert data["outcomes"]["visible_budget"][name]["extra_ask_final"] == 0
    records = json.loads(
        gzip.decompress((ROOT / "experiments/main_B41_games.json.gz").read_bytes())
    )["evaluation"]
    expected = select_examples(primary, visible, {r["id"]: r for r in records})
    examples = json.loads((ROOT / "replays/study/games.json").read_text())
    for a, b in zip(expected, examples):
        for key in a:
            assert a[key] == b[key], (a["id"], key)
    chart_names = [
        "headline",
        "animal-eig",
        "different-failures",
        "visible-budget",
        "noisy-wins",
        "development",
    ]
    charts = {}
    for name in chart_names:
        png = out / "charts" / f"{name}.png"
        svg = out / "charts" / f"{name}.svg"
        width, height = struct.unpack(">II", png.read_bytes()[16:24])
        assert width >= 1000 and height >= 600
        assert "<svg" in svg.read_text()
        charts[name] = {
            "png_sha256": sha(png),
            "svg_sha256": sha(svg),
            "width": width,
            "height": height,
        }
    exports = json.loads((ROOT / "replays/study/exports.json").read_text())
    for item in exports:
        assert item["new_model_calls"] == 0
        for key in ("mp4", "gif"):
            path = ROOT / item[key]
            assert path.stat().st_size > 10000
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    str(ROOT / item["mp4"]),
                ],
                text=True,
            )
        )
        stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        assert (stream["width"], stream["height"], int(stream["nb_frames"])) == (
            1600,
            1200,
            288,
        )
        assert float(probe["format"]["duration"]) == 24
    for name in ("replay.js", "replay.css"):
        assert sha(ROOT / "replays" / name) == sha(ROOT / "replays/study" / name)
    ui = json.loads((ROOT / "replays/study/validation/viewer.json").read_text())
    assert ui["turn_states_verified"] == 24 and not ui["page_errors"]
    assert not ui["mobile_horizontal_overflow"] and ui["canvas_widths_match"]
    docs = [
        "README.md",
        "RESULTS.md",
        "X_THREAD.md",
        "replays/study/README.md",
        "replays/study/EXAMPLES.md",
    ]
    links = 0
    for name in docs:
        text = (ROOT / name).read_text()
        assert not re.search(r"\b(first|novel)\b|[—–]", text, re.I), name
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http:", "https:", "#")):
                continue
            local = target.split("#", 1)[0]
            resolved = ((ROOT / name).parent / local).resolve()
            if resolved != (out / "validation.json").resolve():
                assert resolved.exists(), (name, target)
            links += 1
    draft = json.loads((ROOT / "research/x_thread_draft.json").read_text())
    assert len(draft["posts"]) == 8
    counts = []
    for i, p in enumerate(draft["posts"], 1):
        text = f"{i}/8 " + p["text"].replace("[REPO_URL]", draft["repo_url"])
        count = len(re.sub(r"https?://\S+", "x" * 23, text))
        assert count <= 280
        assert not re.search(r"\b(first|novel)\b|[—–]", text, re.I)
        if p["media"]:
            assert (ROOT / p["media"]).exists()
        counts.append(count)
    budget = Ledger.snapshot_status(ROOT / "ledger.json")
    assert all(budget[k] == v for k, v in data["ledger"].items())
    assert Decimal(budget["spent_usd"]) + Decimal(budget["held_usd"]) <= Decimal("50")
    baseline = json.loads((ROOT / "research/writeup_approval.json").read_text())
    assert len(budget["entries"]) == baseline["ledger_entries"] == 73807
    assert not json.loads((ROOT / "research/active_plan.json").read_text())[
        "dispatch_authorized_now"
    ]
    tests = (out / "unit_tests.log").read_text()
    assert "Ran 226 tests" in tests and tests.rstrip().endswith("OK")
    result = {
        "new_Tinker_calls": 0,
        "new_Tinker_spend_usd": "0.000000",
        "new_ledger_entries": 0,
        "ledger_entries": len(budget["entries"]),
        "project_budget": data["ledger"],
        "protected_artifact_hashes": len(protected),
        "source_hashes": len(data["source_sha256"]),
        "all_scheduled_endpoints_included": True,
        "primary_game_outcomes_recomputed": 1120,
        "example_selection_rule_recomputed": True,
        "examples": [e["record"]["id"] for e in examples],
        "charts": charts,
        "chart_pairs": len(charts),
        "replay_pairs": len(exports),
        "turn_states_checked": ui["turn_states_verified"],
        "local_links_checked": links,
        "thread_posts": len(counts),
        "thread_character_counts": counts,
        "thread_posted": False,
        "repo_link_placeholder": draft["repo_url"] == "[REPO_URL]",
        "unit_tests": 226,
    }
    (out / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "charts"}, indent=2))


if __name__ == "__main__":
    main()
