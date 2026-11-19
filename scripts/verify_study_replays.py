"""Check every saved turn against the rendered viewer and inspect local media."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.async_api import async_playwright
from twenty_bits.worlds import ROOT


async def main():
    folder = ROOT / "replays/study"
    examples = json.loads((folder / "games.json").read_text())
    out = folder / "validation"
    out.mkdir(exist_ok=True)
    errors = []
    states = 0
    async with async_playwright() as playwright:
        system_chrome = Path(
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        options = (
            {"executable_path": str(system_chrome)} if system_chrome.exists() else {}
        )
        browser = await playwright.chromium.launch(**options)
        page = await browser.new_page(
            viewport={"width": 1600, "height": 1200}, device_scale_factor=1
        )
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        for example in examples:
            await page.goto(
                (folder / "compositions" / f"{example['id']}.html").as_uri()
            )
            await page.evaluate("document.fonts.ready")
            maximum = max(len(p["trace"]["turns"]) for p in example["players"])
            for step in range(maximum + 1):
                await page.evaluate("(t) => window.setReplayTime(t)", step * 2)
                actual = await page.evaluate("""() => ({
                  players: [...document.querySelectorAll('.player:not([hidden])')].map(p => ({
                    action: p.querySelector('.question').textContent,
                    answer: p.querySelector('.answer').textContent,
                    count: p.querySelector('.remaining').textContent,
                    used: p.querySelector('.question-count').textContent,
                    eliminated: [...p.querySelectorAll('.candidate')].map(n=>n.classList.contains('eliminated')),
                    outcome: p.querySelector('.outcome').textContent
                  })),
                  width: document.querySelector('#sheet').getBoundingClientRect().width,
                  footer: document.querySelector('footer').getBoundingClientRect().bottom
                })""")
                assert len(actual["players"]) == len(example["players"])
                assert actual["width"] == 1600 and actual["footer"] <= 1200
                limit = 2 * (example["record"]["n"] - 1).bit_length()
                for panel, player in zip(actual["players"], example["players"]):
                    trace = player["trace"]
                    completed = min(step, len(trace["turns"]))
                    turn = trace["turns"][completed - 1] if completed else None
                    posterior = (
                        turn["posterior_after"]
                        if turn
                        else [1 / example["record"]["n"]] * example["record"]["n"]
                    )
                    assert panel["action"] == (
                        turn["action"] if turn else "Every candidate is equally likely."
                    )
                    assert panel["answer"] == (turn["answer"] if turn else "—")
                    assert panel["eliminated"] == [p == 0 for p in posterior]
                    if example["record"]["noise"]:
                        top = posterior.index(max(posterior))
                        count = sum(
                            p > 0.001 or i == top for i, p in enumerate(posterior)
                        )
                    else:
                        count = sum(p > 0 for p in posterior)
                    assert panel["count"] == str(count)
                    used = sum(t["is_question"] for t in trace["turns"][:completed])
                    assert panel["used"] == f"{used} / {limit}"
                    if completed == len(trace["turns"]):
                        assert panel["outcome"] == (
                            "Correct guess"
                            if trace["won"]
                            else "No guess: extra ASK"
                            if trace["guess_state"] is None
                            else "Wrong guess"
                        )
                states += 1
                if step in (0, maximum // 2, maximum):
                    await page.screenshot(
                        path=str(out / f"{example['id']}-{step * 2}.png")
                    )
            await page.evaluate("(t) => window.setReplayTime(t)", 22)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto((folder / "viewer/index.html").as_uri())
        await page.evaluate("document.fonts.ready")
        assert await page.evaluate("document.documentElement.scrollWidth") <= 390
        await page.select_option("#example", "1")
        assert await page.locator(".player:not([hidden])").count() == 2
        await page.select_option("#example", "0")
        assert await page.locator(".player:not([hidden])").count() == 3
        await page.uncheck("#reveal")
        assert await page.locator(".target-cell").count() == 0
        await page.check("#reveal")
        assert await page.locator(".target-cell").count() == 3
        await page.screenshot(path=str(out / "mobile.png"), full_page=True)
        await browser.close()
    assert not errors, errors
    exports = json.loads((folder / "exports.json").read_text())
    for export in exports:
        assert export["duration_seconds"] == 24 and export["frames"] == 288
        assert (export["width"], export["height"]) == (1600, 1200)
        assert export["fps"] == "12/1"
        for second in (0, 10, 22):
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    str(second),
                    "-i",
                    str(ROOT / export["mp4"]),
                    "-frames:v",
                    "1",
                    str(out / f"rendered-{export['name']}-{second}.png"),
                ],
                check=True,
            )
    result = {
        "new_model_calls": 0,
        "turn_states_verified": states,
        "policies_in_comparisons": [3, 2],
        "exact_actions_answers_posteriors": True,
        "canvas_widths_match": True,
        "footer_within_canvas": True,
        "mobile_width": 390,
        "mobile_horizontal_overflow": False,
        "example_switch_and_target_toggle": True,
        "page_errors": errors,
        "media": exports,
    }
    (out / "viewer.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
