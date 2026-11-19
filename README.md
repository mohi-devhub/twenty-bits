# Twenty Bits

![Animal question quality and the different ways games end](results/writeup/charts/headline.png)

![Base wins while A11 gambles and A23 stalls on the same target](replays/study/gamble-stall.gif)

- Qwen3-8B plays table-based 20 Questions with candidate state supplied. Reward pays for wins and charges for questions and invalids. EIG is measured, never rewarded.
- Noiseless animal EIG/question improves from raw **0.158** to **0.634, 0.390 and 0.437** across all three seeds. Conditional 95% CIs appear in [RESULTS.md](RESULTS.md).
- A11 and A23 win **24/56 and 25/56** animal games, but A11 makes **32 ambiguous wrong guesses** and A23 leaves **31 without guessing**.
- An eval-only budget counter removes A23's **136 no-guess endings** and raises wins **138 to 186/280**. B41's ambiguous guesses with budget left fall only **202 to 188/280**.
- Under the primary prompt, noisy wins are **raw 52/140, A11 31, A23 29, B41 36**. Noisy training does not clearly help. Under visible budget, A23's noisy wins rise to **74/140**.

[Results, confidence intervals and limitations](RESULTS.md) · [Every derived number and source hash](results/writeup/numbers.json) · [X thread draft for review](X_THREAD.md)

The study has two truthful-training seeds and one noisy-training seed. Each frozen cell has 28 games. Animal rows are authored profiles, the grammar is fixed, and thinking is disabled. Synthetic transfer is mixed. All scheduled endpoints and failed configurations remain available. The examples use a [disclosed selection rule](replays/study/README.md), including a case where the base model wins and both trained models lose.

Recorded Tinker usage is **$23.681223**, plus **$2.083181 held** pending reconciliation, under the **$50 cap**. Available budget is **$24.235596**. These are observed-token charges at pinned prices, not a reconciled invoice. The write-up and local exports add zero Tinker spend. [Ledger](ledger.json), [hold breakdown](BUDGET.md).

## Reproduce the write-up offline

Use Python 3.11 or later. The commands below read saved results and do not construct a service client.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[paid,replay]'
python3 scripts/build_writeup_data.py
python3 scripts/plot_writeup.py
python3 scripts/build_study_replays.py
python3 scripts/verify_writeup.py
python3 -m unittest discover -s tests -v
```

The committed PNG and SVG pairs are in [results/writeup/charts](results/writeup/charts). The development curves use the same small noiseless development slice for all seeds. They do not measure noisy or large-N performance. [Statistical definitions](NUMBERS.md), [write-up verification](results/writeup/validation.json).

## Watch and rebuild the replays

[Interactive viewer](replays/study/viewer/index.html) · [Base / A11 / A23 MP4](replays/study/gamble-stall.mp4) · [A23 primary / visible-budget MP4](replays/study/budget-fix.mp4) · [Budget-fix GIF](replays/study/budget-fix.gif) · [Full example transcripts](replays/study/EXAMPLES.md)

Serve the repository with `python3 -m http.server 8765`, then open `http://localhost:8765/replays/study/viewer/`. Play, scrub, switch between the two cases, or hide the target. Question counters and posterior shading are viewer annotations. The primary policies did not see a remaining-budget counter.

Local video export needs Node.js 22 or later and FFmpeg:

```bash
python3 scripts/export_study_replays.py
```

The export uses the pinned HyperFrames CLI and the existing replay viewer. It replays saved actions, answers and posteriors. It never samples a model. To rebuild only the GIFs from existing videos, add `--reuse-mp4`. [Replay construction, selection and checks](replays/study/README.md).

## Read the code and experimental record

[LEARN.md](LEARN.md) explains the phases in plain language. Start with [worlds.py](twenty_bits/worlds.py), [predicates.py](twenty_bits/predicates.py), [information.py](twenty_bits/information.py) and [game.py](twenty_bits/game.py). Then read [candidate_feedback.py](twenty_bits/candidate_feedback.py), [rl_pilot.py](twenty_bits/rl_pilot.py) and [the final data builder](scripts/build_writeup_data.py).

[PROTOCOL.md](PROTOCOL.md) fixes the game and primary observations. [NUMBERS.md](NUMBERS.md) records the declared comparisons. [PRIOR_WORK.md](PRIOR_WORK.md) supplies context. Primary endpoint tables remain in [the B41 gate](MAIN_B41_GATE.md); the separate prompt intervention remains in [the visible-budget gate](VISIBLE_BUDGET_GATE.md). The old no-list failure, SFT, pilot, parser diagnostic and tiny hard-mode results are retained rather than merged into the main RL comparison.

Live spending state uses ignored SQLite storage. [ledger.json](ledger.json) is the completed audit export. Historical gate checks belong at their corresponding commits because their ledger exports and protected source hashes are fixed there. Do not rerun old summary writers against today's ledger. Credentials, run caches and adapter binaries remain ignored.

**The experimental phase is complete. No more training or evaluation is authorized unless the user asks. The thread is a draft and has not been posted.**
