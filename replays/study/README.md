# Saved model replays

These animations use accepted saved actions, answers and posterior arrays. They make no model calls. Both comparisons share a target within the comparison. The two selected cases also happen to share the same table and target across noise modes. [Selection record](../../results/writeup/numbers.json), [full transcripts](EXAMPLES.md).

## How the examples are selected

`scripts/build_writeup_data.py` orders animal cells by ascending N, then by ascending numeric frozen index. It applies these behavior filters before taking the earliest eligible case:

- For the truthful three-player replay, A11 must make an ambiguous wrong guess with questions left, and A23 must finish without a guess. Raw base uses that case without an outcome filter. There are 23 eligible cases. The selected ID is `paid-v1/animals/32/1/p0`.
- For the noisy budget replay, A23 primary must finish without a guess and A23 visible budget must win. There are 13 eligible cases. The selected ID is `paid-v1/animals/32/1/p0.1`.

Neither rule filters question text, game length, EIG or target. The rules were chosen during the write-up, after the experimental phase. These filters intentionally illustrate failure differences. They are not an unbiased performance sample. All declared games remain in the aggregate charts.

In the truthful replay, base wins after seven questions, A11 loses after guessing with two candidates left, and A23 attempts another ASK after ten questions. In the noisy replay, A23 visible budget wins with 13 displayed candidates and target posterior about 0.571. That win does not imply certainty. [Saved states](games.json).

## What the viewer shows

The grid greys out zero-posterior candidates in truthful play. Noisy shading represents posterior weight rather than exact elimination. The noisy candidate count matches the supplied list: probability above 0.001 plus MAP. Numeric posterior weights, target outlines, flip notifications and viewer counters are annotations for the reader. Primary policies see candidate names but do not see the running budget counter.

The action text is complete. The line below ASK text expands exact column codes into attribute names for the reader. The renderer does not repair questions or rescore answers. The three-player case uses Raw, A11 and A23. The two-player case uses the same A23 endpoint with the original prompt and the visible-budget amendment.

[Interactive controls](viewer/index.html) · [truthful three-player MP4](gamble-stall.mp4) · [truthful GIF](gamble-stall.gif) · [noisy budget MP4](budget-fix.mp4) · [noisy GIF](budget-fix.gif)

## Rebuild locally

From the repository root:

```bash
python3 scripts/build_writeup_data.py
python3 scripts/build_study_replays.py
python3 scripts/export_study_replays.py
```

The shared viewer source is `replays/replay.js` and `replays/replay.css`. The builder mirrors that code and the licensed local fonts into this folder. The study-specific stylesheet controls layout. It retains the existing deterministic GSAP timeline with two seconds per action and an ending hold. The root compositions are 1600 by 1200 pixels. Local export uses `hyperframes@0.9.63`, 12 frames per second, and FFmpeg. Each MP4 is 24 seconds with 288 frames. GIFs use six frames per second and width 1400. [Export metadata](exports.json).

Install the replay extra with `python3 -m pip install -e '.[replay]'`. UI verification uses Playwright with a local Chromium installation. HyperFrames manages its local render browser. No service credentials are needed. To rebuild only GIFs, use `python3 scripts/export_study_replays.py --reuse-mp4`.

The local HyperFrames runtime, layout and contrast check and the saved-frame/UI checks are recorded under [validation](validation). Both exported videos are visually checked at the same saved turn times. Runtime, layout and contrast checks pass. Authoring and craft warnings flag the single-scene structure, dense typography under a generic phone-size threshold and intentional silence. [Write-up verification](../../results/writeup/validation.json).

The CLI also offers the [HyperFrames desktop app](https://hyperframes.studio/studio/download?src=cli) for editing the local composition with Framey. The checked-in HTML remains the reproduction source.
