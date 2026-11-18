"""Write the candidate-set gate from verified saved results and token forecasts."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def interval(point, bounds, *, percent=False):
    scale = 100 if percent else 1
    suffix = "%" if percent else ""
    return (
        f"{point * scale:.1f}{suffix} [{bounds[0] * scale:.1f}, {bounds[1] * scale:.1f}]"
        if percent
        else f"{point:.3f} [{bounds[0]:.3f}, {bounds[1]:.3f}]"
    )


def main():
    summary = json.loads((ROOT / "results/candidate_set/summary.json").read_text())
    proposal = json.loads(
        (ROOT / "research/candidate_set_pilot_proposal.json").read_text()
    )
    policies = summary["policies"]
    lines = [
        "# Candidate-set qualification gate",
        "",
        "Completed 2026-11-18. **Both policies pass qualification; no new training or RL ran.** The existing SFT checkpoint reached 91.9% valid turns and 14/32 wins. Raw Qwen3-8B reached 98.5% and 23/32. Recommend raw base for the proposed pilot, subject to the user's choice. The main task now measures question selection given supplied candidate state, not independent state tracking.",
        "",
        "## Frozen observation change",
        "",
        "`candidate-set-v1` appends the exact consistent list after noiseless question answers, including INVALID. With p=0.10 it appends items with posterior probability strictly above **0.001**, plus the MAP candidate, and labels the top candidate. This absolute threshold never changes across turns, sizes or domains. Ties use original TABLE order. Noisy candidates may re-enter; the displayed list is not certain elimination. The threshold is below the uniform prior probability for every planned N. Answer and EIG calculations still use the complete table and posterior. No new action restriction is imposed.",
        "",
        "The only prompt addition is the state-feedback contract and lists. The grammar-example rules, random syntax examples, table, reward (+1 win, -0.03/question, -0.1/invalid), original-N budget, exact aliases, 2,048 output cap, disabled thinking, temperature 0.7, top-p 1 and top-k disabled remain fixed. Every old list stays in history. The system table/rules prefix is stable across turns and noise modes, so new feedback does not break that prefix. No EIG reward was introduced.",
        "",
        "All 2,000 frozen games retain their targets, subsets, seeds and file hashes. [New hashes](evals/candidate_set/prompt_hashes.json) record native initial prompts for the main and no-list hard modes. [Old Phase 2 hashes](evals/frozen/prompt_hashes.json) remain untouched. Future model-dependent histories are hashed separately; [SFT](results/candidate_set/format_sft/prompt_hashes.json) and [raw-base](results/candidate_set/raw_base/prompt_hashes.json) sampled prompt hashes are saved. Native/cookbook token sequences matched before and during sampling.",
        "",
        "The no-list grammar-example format remains evaluation-only hard mode for RL. [The hard-mode slice](evals/hard_mode.json) fixes indices 0 and 1 in all ten cells, 20 games each for raw base and the final model, to be run at the end. Those games have not been sampled under this approval. They are not training examples. The prior format SFT is the explicitly accepted exception: it already used no-list toy transcripts. Original Phase 2 is historical data under a different prompt, not a matched RL control.",
        "",
        "## Paired training-pool qualification",
        "",
        "Both policies played the same 32 cases as the earlier qualification: 16 each at N=4 and N=8, p=0, animals training pool only, game seed 20261120 and indices 600000 through 600015. The generation namespace remains `format-qualification-policy-v1`, so per-turn requested seeds match across policies and the earlier SFT qualification. The SFT sampler loaded the exact saved native checkpoint from the completed 36-update warm start; it did not train again. Raw base used no adapter. No frozen case entered this run.",
        "",
        "The declared pass rule is at least 90% pooled valid turns and 8/32 wins. Valid turns include legal guesses that lose; another ASK in the final-guess slot is invalid as a turn but does not increase counted questions. This distinction explains the gap between invalid-turn and invalid-question rates.",
        "",
        "| Policy | N | Valid turns [95% CI] | Wins [Wilson 95% CI] | EIG/question [95% CI] | Questions/win [95% CI] |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for policy in ("raw_base", "format_sft"):
        for c in policies[policy]["cells"]:
            m = c["metrics"]
            lines.append(
                f"| {policy} | {c['n']} | {c['valid_turns']}/{c['turns']} = "
                + interval(
                    c["valid_turn_rate"],
                    c["valid_turn_ci95_game_bootstrap"],
                    percent=True,
                )
                + f" | {c['wins']}/16; "
                + interval(c["win_rate"], c["win_wilson_ci95"], percent=True)
                + " | "
                + interval(m["eig_per_question"], m["eig_per_question_ci95"])
                + " | "
                + interval(m["questions_per_win"], m["questions_per_win_ci95"])
                + " |"
            )
    comparison = summary["paired_comparison"]
    win = comparison["win_rate"]
    eig = comparison["eig_per_question"]
    lines.extend(
        [
            "",
            f"SFT minus raw base is **{win['sft_minus_raw_base'] * 100:.1f} percentage points** in wins (paired 95% CI [{win['paired_ci95'][0] * 100:.1f}, {win['paired_ci95'][1] * 100:.1f}]) and **{eig['sft_minus_raw_base']:.3f} bits/question** (CI [{eig['paired_ci95'][0]:.3f}, {eig['paired_ci95'][1]:.3f}]). These are 10,000 paired whole-game bootstrap draws stratified by N. Per-cell metric CIs resample games; Wilson win bounds retain finite-sample uncertainty. One small development slice and one SFT seed do not establish a general SFT effect.",
            "",
            "No new raw-base no-list run was authorized, so the feedback effect cannot be separated for raw base. On the same earlier SFT cases without lists, it won 3/32; with lists, 14/32. The main raw-base-versus-SFT comparison holds the supplied-state prompt fixed. Raw base's stronger result supports omitting an unnecessary SFT prior, while the existing SFT checkpoint remains eligible if chosen.",
            "",
            "## Behavior and remaining failures",
            "",
            "Both policies had **zero item-name enumeration**, zero output truncations, zero visible reasoning tokens, zero guesses of eliminated items and zero wrong guesses at singleton. Raw base won every one of its 19 singleton-reaching games. SFT won 10 of 11; the remaining game failed to guess after its budget. The supplied list addressed the previously observed wrong-guess consistency failure on these cases. It did not make question selection optimal.",
            "",
            "| Policy | Repeated splits | Valid zero-EIG questions | Wrong guess among remaining | No final guess after budget |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for policy, a in policies.items():
        lines.append(
            f"| {policy} | {a['repeated_splits']} | {a['valid_zero_eig_questions']} | {a['loss_causes'].get('wrong_guess_among_remaining_candidates', 0)} | {a['loss_causes'].get('no_final_guess_after_budget', 0)} |"
        )
    lines += [
        "",
        "Remaining invalid-turn causes: raw base had one invented attribute (`horn`) at N=8 and one non-GUESS action after budget at N=4. SFT had one invented attribute (`no_flippers`) at N=8 and 11 non-GUESS final-slot actions (four at N=4, seven at N=8). No guess named an item outside the original table. Enumeration is still legal and will be audited during RL rather than prohibited.",
        "",
        "Mean native predicate lengths were 7.77 and 3.73 tokens for raw base at N=4 and N=8, versus 2.11 and 2.24 for SFT. These counts include malformed questions, as in the fixed protocol. [Complete metrics and intervals](results/candidate_set/summary.json) retain every cell and audit.",
        "",
        "## Measured tokens, caching and cost",
        "",
        "Initial mean prompt lengths are **670.19 tokens at N=4** and **787.94 at N=8**, identical across both policies. Later lengths are measured from complete native token sequences. Candidate lists can shrink per game while conditional averages among still-running games rise. Historical lists are retained, so full prompt length grows even when the latest list gets shorter. [Offline frozen-grid and baseline measurements](research/candidate_set_tokens.json) and per-policy `token_counts.json` preserve the counts.",
        "",
        "| Policy | N | Input tokens | Generated tokens | Cache hit tokens | Cache hit % | Recorded USD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for policy, a in policies.items():
        for c in a["cells"]:
            lines.append(
                f"| {policy} | {c['n']} | {c['prompt_tokens']:,} | {c['output_tokens']:,} | {c['prompt_cache_hit_tokens']:,} | {100 * c['prompt_cache_hit_tokens'] / c['prompt_tokens']:.1f} | {c['actual_usd_complete_games']} |"
            )
    cost = summary["cost"]
    status = cost["project"]
    lines.extend(
        [
            "",
            f"The prior SFT actions re-rendered with candidate feedback forecast $0.022656 per policy, or **$0.045312 uncached** combined. The observed new trajectories would cost **$0.048259 uncached**; observed cache hits lowered recorded usage to **${cost['recorded_usage_usd']}**, with **${cost['held_usd']} new holds**, below the **$0.50** combined limit. Independent $0.25 per-policy guards enforce that combined cap. Every call, including metadata and checkpoint loading, used Ledger.call. Every new sampling ID was saved before dispatch and checked against its receipt. No replacement or new checkpoint save was needed.",
            "",
            f"Project usage is **${status['spent_usd']}**, existing holds **${status['held_usd']}**, and **${status['available_usd']} remains** under $50. The nine excluded originals retain $0.012813 and the earlier bounded storage operations retain $0.10. These recorded token charges use published rates; invoice reconciliation remains pending. The 408, network-recovery and hold rules are unchanged.",
            "",
            "## Pilot proposal — not authorization",
            "",
            "Recommend **raw Qwen3-8B**. The SFT variant is also qualified and is priced separately. Whichever initialization is approved becomes the matched pre-RL main-condition control. The main claim is outcome-only learning of question selection with supplied state. If raw base is selected, its RL branch has no SFT gradients or synthetic-toy training; the separate SFT diagnostic remains reported. If SFT is selected, disclose its random-attribute prior and toy-table exposure when interpreting strategy and transfer.",
            "",
            "Condition A only, seed 11, rank-32 LoRA, 16 updates, one group of eight independent games from one start state per update: **4 updates at N=4, 8 at N=8, 4 at N=16**, 128 training games. Future RL uses animals training_game only and candidate feedback on every rollout. Keep reward, grammar, aliases, 2,048 output cap and disabled thinking unchanged. Group advantages subtract mean return and divide by population standard deviation plus 1e-8. No EIG reward.",
            "",
            "Log reward, wins, questions, EIG and group return variance on every update. Use the same eight separate development games at updates **0, 4, 8, 12 and 16** (40 sampled games total). After four updates, **halt if fewer than 25% of the four groups have nonzero return variance**. One nonconstant group equals 25% and passes. Report win variation separately because question costs can create variance without wins; no extra stop rule has been added.",
            "",
            "| Initialization | Sampling, gradients and 40 dev games | Checkpoint hold allowance | Total ×1.5 | Proposed cap including holds |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for policy, p in proposal["alternatives"].items():
        a = p["scenarios"]["measured_output_full_budget"]
        work = (
            a["training_sampling_usd"]
            + a["training_gradient_usd"]
            + a["development_sampling_usd"]
        )
        lines.append(
            f"| {policy} | ${work:.3f} | ${a['checkpoint_holds_usd']:.2f} | ${a['total_with_1_5_margin_usd']:.2f} | ${p['proposed_run_ceiling_including_holds_usd']} |"
        )
    stress = proposal["alternatives"]["raw_base"]["scenarios"]["output_cap_stress"][
        "total_with_1_5_margin_usd"
    ]
    lines.extend(
        [
            "",
            f"The forecast measures 40 native training-pool prefixes per N, uses the largest measured full-budget trajectory with all candidates retained, and charges uncached inputs and full per-turn gradient contexts. Output proxies come from each measured policy; **N=16 model behavior is unmeasured** and uses N=8's output proxy. Full output-cap stress costs about **${stress:.2f} with margin**, above the proposed $2 ceiling. This is a stress scenario, not an expected bill. If reservations would breach an approved ceiling, halt and retain pending work rather than changing settings or spending more. The $0.30 storage amount is a conservative hold allowance, not a charge. [Reproducible forecasts and both initialization choices](research/candidate_set_pilot_proposal.json).",
            "",
            "The pilot gate will include the early-guess, repeated/singleton search, large-name-list and parser-exploit audit, learning curves, and revised main-run Options S and U. A raw-base recommendation is a proposal, not a silently changed initialization. **No RL is authorized or started. Stop for the user's pilot decision.**",
        "",
        "These results cover only small, noiseless animal development games. No transfer, noisy or frozen-test model evaluation has run under the candidate-set format. No RL improvement has been measured. The authored profiles share underlying animal types, the grammar is structured, and noisy threshold feedback supplies computed belief information; later claims must retain those limits.",
            "",
            "## Verification and reproduction",
            "",
            "107 unit tests pass, including strict threshold boundaries, MAP ties, noisy re-entry, no target access, stable prefixes, INVALID feedback and guarded raw/checkpoint sampler selection. Frozen files and old hashes are unchanged. [Validation](results/candidate_set/validation.json) verifies paid request IDs, matching prompts, unchanged historical ledger entries and the absence of training operations. [Archive reproduction](results/candidate_set/reproduction.json) verifies analysis without local run caches.",
            "",
            "Run offline: `python3 scripts/summarize_candidate_qualification.py`, `python3 scripts/price_candidate_pilot.py`, `python3 scripts/write_candidate_gate.py`. The only live entry point is `scripts/run_candidate_qualification.py`; completed runs refuse new service calls. No pilot runner is active.",
            "",
        ]
    )
    (ROOT / "CANDIDATE_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
