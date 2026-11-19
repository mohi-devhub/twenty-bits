"""Write the A23 gate from verified primary and auxiliary measurements."""

from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.write_main_seed_gate import num, percent, interval, bins
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.worlds import ROOT


def read(name):
    return json.loads((ROOT / name).read_text())


def stage_cost(status, run_id):
    entries = [e for e in status["entries"] if e["operation"].startswith(f"[{run_id}] ")]
    return {
        "spent": str(sum((Decimal(e["actual_usd"]) for e in entries if e["state"] == "settled"), Decimal(0))),
        "held": str(sum((Decimal(e["reserved_usd"]) for e in entries if e["state"] in ACTIVE_STATES), Decimal(0))),
    }


def main():
    s = read("results/main_A23/summary.json")
    replication = read("results/main_A23/replication_summary.json")
    a11 = read("results/main_A11/summary.json")
    completion = read("results/main_A23/completion.json")
    validation = read("results/main_A23/validation.json")
    proof = read("research/main_A23_preflight.json")
    assessment = read("research/main_A23_assessment.json")
    recovery = read("research/main_A23_network_recovery.json")
    io_diagnostic = read("research/A23_ledger_io_diagnostic.json")
    variation = read("results/A23_suffix/session_variation.json")
    status = Ledger(ROOT / "ledger.json").status()
    lines = ["# Main A seed 23 gate", "",
        "Completed 30 updates, 240 training games, 64 new development games and the scheduled 280-game frozen endpoint. The matched raw frozen control (280 games) and raw development control (8 games) are reused from their unchanged archives. Immediate endpoint evaluations also completed: 168 labelled suffix-diagnostic games and 40 hard-mode games (20 raw base, 20 A23). **B41 has not started; work stops at this gate.**", "",
        *[line for paragraph in assessment["learning_assessment"] for line in (paragraph, "")],
        "![A23 learning curve](results/main_A23/charts/main-learning.png)", "",
        "## Fixed setup", "",
        "Provider-base Qwen3-8B, no project SFT or pilot adapter; rank-32 LoRA seed 23; learning rate 4e-5 and unchanged Adam parameters. One eight-game group from one start state per update; group-standardized outcome-only returns. Reward: +1 win, -0.03/question, -0.1/INVALID. EIG is measured, never rewarded. Thinking is disabled, output cap 2,048, context cap 32K. Candidate feedback, grammar, aliases, generation settings and original-N question budgets are unchanged.", "",
        "| N | Updates | Training games |", "| ---: | --- | ---: |"]
    for r in proof["curriculum"]:
        lines.append(f"| {r['n']} | {r['update_start']}–{r['update_end']} | {8*(r['update_end']-r['update_start']+1)} |")
    lines += ["", "The curriculum reaches **N=32 and N=128**, matching the frozen animal cells. All gradients use only the fixed 200-row animal training pool. Frozen cases, development cases, held-out rows and synthetic tables never enter gradients. Only the scheduled endpoint is retained; no selection uses frozen scores.", "",
        "## All 30 training updates", "",
        "Groups are sampled before their corresponding optimizer step. Different group targets and curriculum stages confound raw training slopes; the fixed development checks provide a matched curve. EIG includes losses and INVALID. Questions/win is conditional and can fall below log2(N) after uncertain or lucky guesses.", "",
        "| Update | N | Reward | Wins/8 | EIG/Q | Q/win | Enum % | Invalid % | Nonzero group / cumulative % | Output tokens/game |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
    for r in s["updates"]:
        lines.append(f"| {r['update']} | {r['n']} | {num(r['mean_reward'])} | {r['wins']}/8 | {num(r['eig_per_question'])} | {num(r['questions_per_win'],2)} | {percent(r['enumeration_rate'])} | {percent(r['invalid_question_rate'])} | {percent(r['nonzero_group_fraction'])} / {percent(r['cumulative_nonzero_group_fraction'])} | {num(r['output_tokens_per_game'],2)} |")
    signal = s["group_signal_audit"]
    lines += ["", f"Nonconstant returns: {signal['nonconstant_return_groups']}/30 groups. Win variance: {signal['groups_with_win_variance']}/30. Zero-win groups with cost-only variance: {signal['zero_win_groups_with_cost_only_variance']}.", "",
        "## Fixed development curve: A11 versus A23", "",
        "Each check uses the same four N=4 and four N=8 cases and requested generation seeds. None enters gradients. Raw development is reused; no new raw-control charge occurs. EIG intervals resample eight complete games and remain descriptive.", "",
        "| Update | Seed | Reward | Wins/8 | EIG/Q [95% CI] | Q/win | Output tokens/game |",
        "| ---: | --- | ---: | ---: | --- | ---: | ---: |"]
    for step in s["development"]:
        for label, summary in (("A11",a11),("A23",s)):
            d=summary["development"][step];r=d["point"]
            lines.append(f"| {step} | {label} | {num(r['mean_reward'])} | {r['wins']}/8 | {interval(r['eig_per_question'],d['ci95']['eig_per_question_ci95'])} | {num(r['questions_per_win'],2)} | {num(r['output_tokens_per_game'],2)} |")
    lines += ["", "## Guess with k remaining", "",
        "Entries are wins/guesses. Noiseless k is exact support; noisy k is the fixed >0.001 plus MAP candidate list. Full positive support is also saved, since a noisy displayed singleton is not certainty. All-game denominators include no-guess endings. This measurement changes no reward or action restriction.", "",
        "| Development update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 8 |",
        "| ---: | --- | --- | --- | --- | ---: |"]
    for step,d in s["development"].items():
        g=d["point"]["guess_with_k_remaining"]
        lines.append(f"| {step} | "+" | ".join(bins(g))+f" | {g['no_guess_games']} |")
    lines += ["", "| Training update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 8 |", "| ---: | --- | --- | --- | --- | ---: |"]
    for r in s["updates"]:
        g=r["guess_with_k_remaining"]
        lines.append(f"| {r['update']} | "+" | ".join(bins(g))+f" | {g['no_guess_games']} |")
    lines += ["", "## Paired frozen evaluation", "",
        "All cells use indices 0–27, with original targets, tables and noise seeds. Raw base, A11 and A23 use the same primary rendering, grammar, sampling settings and requested generation seeds. There are 10,000 paired whole-game bootstrap draws; Wilson win intervals and unadjusted paired tests are in the JSON summaries. The p=0 ceiling is 1 bit/question; p=0.10 has ceiling 0.531004 bits/question.", "",
        "![A23 frozen endpoint](results/main_A23/charts/frozen-endpoint.png)", "",
        "| Domain | N | p | Policy | Wins/28 | EIG/Q [95% CI] | Q/win [95% CI] |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |"]
    for i,r in enumerate(s["frozen_evaluation"]["cells"]):
        for label,m in (("Raw base",r["base"]),("A11",a11["frozen_evaluation"]["cells"][i]["endpoint"]),("A23",r["endpoint"])):
            lines.append(f"| {r['domain']} | {r['n']} | {r['noise']:g} | {label} | {m['wins']}/28 | {interval(m['eig_per_question'],m['eig_per_question_ci95'])} | {interval(m['questions_per_win'],m['questions_per_win_ci95'])} |")
    lines += ["", "| A23 declared subset | Metric | Raw base | A23 | Paired change [95% CI] |", "| --- | --- | ---: | ---: | --- |"]
    for subset,measurements in s["frozen_evaluation"]["declared_subsets"].items():
        for key,h in measurements.items():
            lines.append(f"| {subset} | {key} | {num(h['base'])} | {num(h['endpoint'])} | {interval(h['final_minus_base'],h['ci95'])} |")
    lines += ["", "### Explicit A11 versus A23 comparison", "",
        "| Noiseless animals, equal size weights | A11 | A23 | A23 minus A11 [paired-game 95% CI] |", "| --- | ---: | ---: | --- |"]
    for key,h in replication["noiseless_animal_replication"].items():
        lines.append(f"| {key} | {num(h['A11'])} | {num(h['A23'])} | {interval(h['A23_minus_A11'],h['paired_games_ci95'])} |")
    lines += ["", "Intervals above condition on the two fitted endpoints. A separate hierarchical bootstrap resamples A seeds 11/23 before paired games, preserving policy/noise pairing. With only two A seeds, training-seed uncertainty remains unstable. The following intervals describe the mean A endpoint change relative to the shared raw control; they do not select a seed. [All seed-and-game intervals](results/main_A23/replication_summary.json).", "",
        "| Equal-cell subset | Metric | Hierarchical seed-and-game 95% change interval |", "| --- | --- | --- |"]
    for subset,measurements in replication["hierarchical_seed_and_game_bootstrap"]["ci95_mean_A_endpoint_minus_raw"].items():
        for key,ci in measurements.items():
            lines.append(f"| {subset} | {key} | [{num(ci[0])}, {num(ci[1])}] |")
    lines += ["", "![Both A seeds on matched cases](results/main_A23/charts/A-replication.png)", "",
        "| Frozen cell | Policy | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 28 |", "| --- | --- | --- | --- | --- | --- | ---: |"]
    for i,r in enumerate(s["frozen_evaluation"]["cells"]):
        for label,m in (("Raw base",r["base"]),("A11",a11["frozen_evaluation"]["cells"][i]["endpoint"]),("A23",r["endpoint"])):
            g=m["guess_with_k_remaining"]
            lines.append(f"| {r['domain']} N={r['n']} p={r['noise']:g} | {label} | "+" | ".join(bins(g))+f" | {g['no_guess_games']} |")
    lines += ["", "Invalid and enumeration rates use counted questions; format and truncation rates use generated actions. A non-GUESS at the final-guess opportunity is a format/rule error but adds no counted question. Re-check counts use the next-action opportunities after replies with predictive probability below 0.20. This semantic re-ask measure does not capture every possible cross-check.", "",
        "| Cell | A23 invalid % | Format % | Truncation % | Enum % | Predicate tokens/Q | Re-check/opportunities |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in s["frozen_evaluation"]["cells"]:
        m=r["endpoint"]
        lines.append(f"| {r['domain']} N={r['n']} p={r['noise']:g} | {percent(m['invalid_rate'])} | {percent(m['format_error_rate'])} | {percent(m['truncation_rate'])} | {percent(m['enumeration_rate'])} | {num(m['predicate_tokens'],2)} | {m['low_probability_reasks']}/{m['low_probability_opportunities']} |")
    lines += ["", "## Strategy, stopping and implementation audit", "",
        *[line for paragraph in assessment["behavior_assessment"] for line in (paragraph, "")]]
    train=s["training_audit"]["counts"]
    lines += [f"Training: {train['invalid_questions']}/{train['counted_questions']} INVALID questions; {train['item_equality_questions']} item-equality questions; {train['name_list_questions']} name lists; {train['valid_zero_eig_questions']} valid zero-EIG questions; {train['post_budget_asks']} extra ASK actions rejected at the final-guess opportunity. There are {train['zero_question_guesses']} zero-question guesses; all {train['early_guess_games']} logged early guesses follow singleton support and win. Enumeration stays legal. Accepted predicates, answers, posteriors, EIG, rewards, token signatures and gradient batches are replayed exactly. [Two preselected paired examples](results/main_A23/EXAMPLE_GAMES.md).", "",
        "| Synthetic primary error count/form | A11 | A23 |", "| --- | ---: | ---: |"]
    for key in ("invalid_questions","wrong_prefix_on_real_attribute_suffix","of_those_header_code_prefixed","other_invalid_questions"):
        label="Prefix equals the matching attribute's header code" if key=="of_those_header_code_prefixed" else key
        lines.append(f"| {label} | {replication['synthetic_identifier_errors']['11'][key]} | {replication['synthetic_identifier_errors']['23'][key]} |")
    lines += ["", "### Malformed identity-query attempts — post-hoc diagnostic", "",
        "The unchanged enumeration metric counts legal item-equality predicates. A second, read-only lexical audit counts exact candidate-name references in raw ASK bodies, including invalid bare names and name lists. It neither repairs an action nor changes its EIG or reward. A raw reference alone does not prove intent, but consecutive different bare names expose attempted item-by-item questioning that legal-enumeration counts can miss.", "",
        "| Seed / scope | Counted questions | Invalid name-reference questions | Bare-name questions | Raw name lists | Lists ≥ N/4 names | Consecutive different bare names |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for seed,scopes in replication["post_hoc_raw_candidate_name_audits"].items():
        for scope,audit in scopes.items():
            c=audit["counts"]
            lines.append(f"| A{seed} / {scope} | {c.get('counted_questions',0)} | {c.get('invalid_questions_with_name_references',0)} | {c.get('bare_candidate_name_questions',0)} | {c.get('name_list_questions',0)} | {c.get('lists_at_least_quarter_original_N',0)} | {c.get('consecutive_different_bare_names',0)} |")
    for seed,summary in ((11,a11),(23,s)):
        d=summary["sample_train_logprob_diagnostic"]
        lines += ["", f"A{seed} sampler/trainer logprob diagnostic: update-mean range {d['mean_difference_range_nats']}, max absolute token gap {d['maximum_absolute_token_difference_nats']:.6f} nats. Native token sequences match; the backend cause is unestablished. The unchanged importance-sampling objective uses recorded rollout log probabilities."]
    lines += ["", "The gambling pattern means ambiguous guesses with question budget left. Sparse curriculum exposure at N=128 is a possible cause, stated only as a hypothesis; no causal test or protocol change occurred. [Write-up notes](WRITEUP_NOTES.md).", "",
        "## Suffix-tolerant synthetic diagnostic — auxiliary only", "",
        "Fresh A23 rollouts use the same frozen games, seeds, prompts and sampling settings. Only this auxiliary environment accepts a non-real `<code>_<suffix>` identifier when the suffix uniquely matches one real single-letter-prefixed attribute name. Primary and training parsing remain strict. This changes subsequent answers and histories, so these are fresh games rather than repaired primary scores.", "",
        "| N | p | Primary wins/28 | Diagnostic wins/28 | Primary EIG/Q | Diagnostic EIG/Q | Primary invalid % | Diagnostic invalid % | Identifiers mapped | Questions mapped |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in replication["suffix_diagnostic_only"]:
        p,d=r["primary_A23"],r["diagnostic_A23"]
        lines.append(f"| {r['n']} | {r['noise']:g} | {round(p['win_rate']*28)} | {round(d['win_rate']*28)} | {num(p['eig_per_question'])} | {num(d['eig_per_question'])} | {percent(p['invalid_rate'])} | {percent(d['invalid_rate'])} | {r['mapped_identifiers']} | {r['mapped_questions']} |")
    lines += ["", f"Requested sampling parameters match on every shared turn, including seeds. However, {len(variation['initial_action_divergence_before_mapping'])}/168 pairs produced a different action before any suffix mapping despite identical native prompt tokens and supplied parameters; {variation['identical_complete_action_pairs']}/168 complete action sequences match. The backend/restore cause is unestablished. This session reproduction variation limits attribution of small diagnostic differences to the parser alone. [Saved-response audit](results/A23_suffix/session_variation.json).", "",
        "![Auxiliary suffix diagnostic](results/main_A23/charts/suffix-diagnostic.png)", "",
        "## Hard mode — descriptive only", "",
        "Raw base and A23 play the fixed two games per cell without candidate feedback. Neither model has project SFT exposure; neither was trained in hard mode. Requested generation seeds are paired. With two cases per cell, these are descriptive outcomes with wide uncertainty, not a substitute for the primary evaluation.", "",
        "| Domain | N | p | Raw wins/2 | A23 wins/2 | Raw EIG/Q | A23 EIG/Q |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in replication["hard_mode_descriptive_only"]:
        b,f=r["raw_base"],r["A23_endpoint"]
        lines.append(f"| {r['domain']} | {r['n']} | {r['noise']:g} | {b['wins']} | {f['wins']} | {num(b['eig_per_question'])} | {num(f['eig_per_question'])} |")
    lines += ["", "A11 suffix diagnostic and A11 hard mode: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**. Its local adapter/hashes remain an archive. The 16 failed A11 diagnostic requests produced no usable game and retain $0.023700 in original holds. Both A23 endpoint file types are native and permanent; no external upload is used.", "",
        "## Native checkpoint persistence and cost", "",
        "The user confirmed both smoke files displayed Never expiry. Both smoke files were then deleted; the API returned zero remaining checkpoints for the test run. Pixel Miser checkpoints were not mutated. Test-storage holds remain until billing reconciliation. [Verification and deletion](research/native_persistence_deletion.json).", ""]
    for kind,row in completion["checkpoints"]["30"].items():
        lines += [f"- {kind}: `{row['tinker_path']}`; {row['size_bytes']:,} bytes; API expires_at=`{json.dumps(row['expires_at'])}`; paid-plan monthly estimate ${row['monthly_paid_plan_usd']}."]
    lines += ["", "Permanent-file storage reserves cover 30 days using twice measured smoke sizes plus the usual 1.5x reservation margin. Native API sizes and paths are in the ledger. No expiry is set; future storage still requires reconciliation within the project cap. Recorded usage is token-metered at pinned provider rates, pending invoice reconciliation.", "",
        "| A23 component | Usage USD | Held USD |", "| --- | ---: | ---: |"]
    for label,run_id in (("Primary training/dev/endpoint","main-U-A23-v1"),("Suffix diagnostic","A23-suffix-v1"),("Hard mode","A23-hard-v1")):
        c=stage_cost(status,run_id)
        lines.append(f"| {label} | {c['spent']} | {c['held']} |")
    c=s["cost"]
    lines += ["", f"Primary sampling usage: training ${c['sampling_by_kind_usd']['train']}, development ${c['sampling_by_kind_usd']['dev']}, frozen endpoint ${c['sampling_by_kind_usd']['eval_endpoint']}. Forward/backward usage is ${c['gradient_usd']}; storage remains held rather than settled. The matched raw controls add no new charge.", "",
        "The pre-run primary-only forecast was $7.816614 before margin, or $11.724921 with 1.5x margin, covering training, development, the primary endpoint and native storage. Primary usage plus retained holds is $4.867189. The suffix diagnostic and hard mode are separate additions in the table; total A23-stage usage plus new holds is $5.618808. These figures have different scopes from the primary-only forecast.", "",
        f"Project usage **${status['spent_usd']}**, holds **${status['held_usd']}**, available **${status['available_usd']}** under the unchanged $50 cap. All older lost-original and storage holds remain. The suffix diagnostic is capped at $1.50 including its holds.", "",
        "| Newly sampled primary scope | Calls | Prompt tokens | Cache-hit tokens | Generated tokens |", "| --- | ---: | ---: | ---: | ---: |"]
    for kind,u in s["cost"]["token_usage_by_kind"].items():
        lines.append(f"| {kind} | {u['sampling_calls']:,} | {u['prompt_tokens']:,} | {u['prompt_cache_hit_tokens']:,} | {u['output_tokens']:,} |")
    lines += ["", "## Collection, validation and limits", "",
        f"Validation: {validation['tests_passed']} unit tests; {validation['primary_sampling_requests_verified']} primary sampling IDs/receipts; {validation['primary_mutations_verified']} mutation IDs; 30 reconstructed outcome-only gradient batches; all frozen hashes unchanged; no frozen game in gradients. Completed runners return without service access. [Validation](results/main_A23/validation.json), [archive reproduction](results/main_A23/reproduction.json).", "",
        "Every sampling and training mutation saves its deterministic request ID before dispatch and verifies the receipt. Metadata operations also pass through the ledger. A 408 keeps the same ID and hold. Recovery drains HTTP and collects pending futures before new submissions; eligible lost sampling requests get at most one exact replacement, with retained original holds and permanent original-output exclusion. All cases from this stage are listed below.", "",
        f"A transient network interruption occurred after optimizer update 30 had completed. Snapshot request `{recovery['recovered_snapshot_request_id']}` was saved at {recovery['snapshot_saved_before_dispatch_at']} and collected at {recovery['snapshot_response_received_at']} (115.830 seconds from local ID save to collection). The runner drained HTTP work, reconnected and collected that same request; no sampling, gradient or optimizer request was resubmitted. A subsequent checkpoint retrieval returned 408 and was also re-polled under its original ID. These timestamps measure local collection latency, not server retention time. [Recovery evidence](research/main_A23_network_recovery.json).", "",
        f"During endpoint collection, synchronous guard work on the {io_diagnostic['source_entries']:,}-entry ledger blocked the same event loop used for HTTP. Five runs on a disposable copy measured {io_diagnostic['median_seconds']['total_blocking_seconds']:.3f} seconds median per complete guarded operation (range {io_diagnostic['range_seconds']['total_blocking_seconds'][0]:.3f}–{io_diagnostic['range_seconds']['total_blocking_seconds'][1]:.3f}); a separate profile identified JSON serialization as the main cost. This is a local diagnostic, not an end-to-end speedup estimate or proof that every connection error had this cause. After all active HTTP work drained and no recoverable future remained pending, execution parallelism changed from 16 to 2 games. All 93 mutations were already complete. Ledger code, 45-second HTTP timeout, reservations, holds, 408 behavior, model settings, reward and question/output caps stayed unchanged. [Diagnostic](research/A23_ledger_io_diagnostic.json), [execution record](research/A23_execution_concurrency.json).", "",
        "| Stage | Lost originals / exact replacements | Original held USD | Local ID-save → loss observed (seconds) |", "| --- | --- | ---: | ---: |"]
    for stage,c in validation["replacement_cases"].items():
        lines.append(f"| {stage} | {len(c['cases'])} / {len(c['cases'])} | {c['original_holds_usd']} | — |")
        for case in c["cases"]:
            lines.append(f"| {case['logical_key']} | `{case['original_request_id']}` → `{case['replacement_request_id']}` | {case['original_hold_usd']} | {num(case['save_to_loss_observed_seconds'],3)} |")
    lines += ["", "Lost originals are labelled **orphaned, possibly billed**, remain held and are permanently excluded. The local intervals above run from durable ID save to observed unavailability; they do not establish whether a server accepted the request, completed it, billed it or removed a result. The archived cases include connection/timeout errors and observed loss status. No request gets a second replacement without approval.", "",
        "This study measures question selection with supplied state, authored tables and structured grammar. Held-out animal profiles share underlying types with training. Two A seeds give limited seed uncertainty; B41 has not run, so noisy-training claims remain untested. Hard mode has only 20 games per policy. Disabled visible reasoning does not measure internal computation. Checkpoints, seeds and examples were not selected on frozen scores.", "",
        "Reproduce offline with `python3 scripts/analyze_main_A23.py`, `python3 scripts/analyze_A23_replication.py`, `python3 scripts/plot_main_A23.py`, `python3 scripts/verify_main_A23.py`, then `python3 scripts/write_main_A23_gate.py`.", "",
        "## Next decision", "",
        *[line for paragraph in assessment["next_decision"] for line in (paragraph, "")],
        "**Stopped at the A23 gate. Do not start B41 without the user's confirmation.**", ""]
    (ROOT / "MAIN_A23_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
