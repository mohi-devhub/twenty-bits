"""Compare A seeds on paired frozen games and keep auxiliary results separate."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

from scripts.analyze_main_evaluation import paired_cell
from scripts.analyze_main_seed import write_gzip
from scripts.run_baselines import summarize
from scripts.run_main_A23 import metrics
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.game import Game
from twenty_bits.guess_metrics import guess_state, guess_summary
from twenty_bits.learnability import probe_messages
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT, seed_for
from twenty_bits.attributes import attribute_aliases
from twenty_bits.predicates import ParseError, parse
from twenty_bits.name_reference_audit import audit_name_references


def read_rows(path):
    return [json.loads(line) for line in gzip.open(path, "rt")]


def auxiliary(mode):
    config = json.loads((ROOT / f"experiments/A23_{mode}.json").read_text())
    out = ROOT / f"results/A23_{mode}"
    directory = ROOT / "runs" / config["run_id"]
    session_archive = out / "sessions.json"
    if not session_archive.exists():
        session = json.loads((directory / "sessions.json").read_text())
        assert session["finished"]
        save_json(session_archive, session)
    records = json.loads(gzip.decompress((ROOT / f"experiments/A23_{mode}_games.json.gz").read_bytes()))
    records = {r["id"]: r for r in records}
    paths = sorted((directory / "games").glob("*.json"))
    games = [json.loads(p.read_text()) for p in paths] if paths else read_rows(out / "games.jsonl.gz")
    games.sort(key=lambda g: (g["policy"], g["game_id"]))
    request_paths = sorted((directory / "requests").glob("*.json"))
    requests = [json.loads(p.read_text()) for p in request_paths] if request_paths else read_rows(out / "requests.jsonl.gz")
    excluded = [r for r in requests if r.get("output_allowed") is False or r.get("orphaned")]
    allowed = [r for r in requests if r not in excluded]
    if not request_paths and (out / "excluded_originals.jsonl.gz").exists():
        excluded = read_rows(out / "excluded_originals.jsonl.gz")
    by_entry = {r["entry_id"]: r for r in allowed}
    if not request_paths:
        for r in read_rows(out / "responses.jsonl.gz"):
            by_entry[r["entry_id"]]["response"] = r["response"]
    rendering = Rendering(config["primary_model"], config)
    used = set()
    for g in games:
        record = records[g["game_id"]]
        replay = SuffixDiagnosticGame(record) if mode == "suffix" else Game(record, grammar_version="attribute-codes-v2")
        builder = candidate_messages if mode == "suffix" else probe_messages
        overflow = rendering.prompt(builder(record)).length + 2048 > config["context_window"]
        if overflow:
            replay.done = True
        assert guess_state(g, record) == g["guess_state"]
        assert len(g["turns"]) == len(g["trajectory"])
        for index, (turn, tape) in enumerate(zip(g["turns"], g["trajectory"])):
            prompt = rendering.prompt(builder(record, replay.turns)).to_ints()
            assert tape["ob"] == prompt
            req = by_entry[turn["usage"]["entry_id"]]
            assert req["settled"] and req["request_id_saved_before_dispatch"]
            assert req["request_id"] == req["receipt"]["request_id"] == turn["usage"]["request_id"]
            payload = {"model": config["primary_model"], "prompt_ids": prompt, "sampling_params": req["parameters"]}
            assert hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest() == req["signature"]
            assert req["parameters"]["seed"] == seed_for(config["sampling_seed_namespace"], g["game_id"], index) % 2**31
            assert req["parameters"]["max_tokens"] == 2048 and req["parameters"]["temperature"] == .7
            assert req["response"]["sequences"][0]["tokens"] == tape["tokens"]
            assert rendering.decode(tape["tokens"])["action"] == turn["raw_action"]
            reproduced = replay.step(turn["raw_action"], reasoning_tokens=turn["reasoning_tokens"],
                action_tokens=turn["action_tokens"], predicate_tokens=turn["predicate_tokens"], truncated=turn["truncated"])
            assert reproduced["answer"] == turn["answer"] and reproduced["invalid"] == turn["invalid"]
            assert abs(reproduced["eig"] - turn["eig"]) < 1e-12
            np.testing.assert_allclose(reproduced["posterior_after"], turn["posterior_after"], atol=1e-12, rtol=0)
            if mode == "suffix":
                assert reproduced["suffix_mappings"] == turn["suffix_mappings"]
            used.add(req["entry_id"])
            if not replay.done and rendering.prompt(builder(record, replay.turns)).length + 2048 > config["context_window"]:
                replay.done = True
                overflow = True
        assert overflow == g["context_overflow"]
        assert replay.done and replay.won == g["won"] and abs(replay.reward - g["reward"]) < 1e-10
    assert used == set(by_entry)
    assert not used & {r["entry_id"] for r in excluded}
    assert len(games) == (168 if mode == "suffix" else 40)
    write_gzip(out / "games.jsonl.gz", sorted(games, key=lambda g: (g["policy"], g["game_id"])))
    write_gzip(out / "requests.jsonl.gz", [{k:v for k,v in r.items() if k != "response"} for r in sorted(allowed, key=lambda r:r["key"])])
    write_gzip(out / "responses.jsonl.gz", [{"entry_id":r["entry_id"], "response":r["response"]} for r in sorted(allowed,key=lambda r:r["entry_id"])])
    write_gzip(out / "excluded_originals.jsonl.gz", excluded)
    return games


def unused_budget(games):
    ambiguous = [g for g in games if g["guess_state"] and g["guess_state"]["k_remaining"] > 1]
    return {"games":len(games), "ambiguous_guesses":len(ambiguous),
            "ambiguous_guesses_with_unused_budget":sum(g["questions"] < 2 * int(np.ceil(np.log2(g["n"]))) for g in ambiguous)}


def identifier_forms(games, records):
    """Inspect unknown attribute AST nodes without repairing or rescoring actions."""
    import re
    causes=Counter();identifiers=Counter();forms=Counter();examples=[]
    for g in games:
        if g["domain"]!="synthetic":
            continue
        attrs=records[g["game_id"]]["world"]["attributes"]
        aliases=attribute_aliases(attrs)
        by_suffix={}
        for name in attrs:
            match=re.fullmatch(r"[A-Za-z]_(.+)",name)
            if match:
                by_suffix.setdefault(match[1],[]).append(name)
        for turn in g["turns"]:
            if not turn["is_question"] or not turn["invalid"]:
                continue
            causes[turn.get("error","unknown")]+=1
            if not turn["raw_action"].startswith("ASK:"):
                forms["invalid_action_format"]+=1
                continue
            try:
                expression=parse(turn["raw_action"][4:].strip(),aliases=aliases)
            except ParseError:
                forms["syntax_error"]+=1
                continue
            stack=[expression];unknown=[]
            while stack:
                node=stack.pop();stack.extend(node.children)
                if node.kind=="attribute" and aliases.get(node.value,node.value) not in attrs:
                    unknown.append(node.value)
            if not unknown:
                forms["non_attribute_error"]+=1
            hybrid=False
            for name in unknown:
                identifiers[name]+=1
                match=re.fullmatch(r"([A-Za-z]+)_(.+)",name)
                if match and len(by_suffix.get(match[2],[]))==1:
                    hybrid=True
                    forms["hybrid_identifier_occurrences"]+=1
                    forms["any_active_header_code_prefix_occurrences"]+=match[1] in aliases
                else:
                    forms["other_unknown_attribute_occurrences"]+=1
            forms["questions_with_hybrid_identifier"]+=hybrid
            if unknown and len(examples)<3:
                examples.append({"game_id":g["game_id"],"raw_action":turn["raw_action"],"unknown_attributes":unknown,"error":turn.get("error")})
    return {"forms":dict(forms),"invalid_causes":dict(causes),
            "common_unknown_attributes":identifiers.most_common(5),"examples":examples,
            "method":"Read-only AST audit, including compound predicates; no scoring changes."}


def across_seed_intervals(raw, endpoints, cells, draws=10000):
    rng = np.random.default_rng(20261119)
    seed_draw = rng.integers(2, size=(2, draws))
    case_draws = {}
    deltas = []
    for domain, n, noise in cells:
        indices = case_draws.setdefault((domain, n), rng.integers(28, size=(draws, 28)))
        selector = lambda g: (g["domain"], g["n"], g["noise"]) == (domain, n, noise)
        base = sorted(filter(selector, raw), key=lambda g:g["game_id"])
        final = [sorted(filter(selector, endpoints[seed]), key=lambda g:g["game_id"]) for seed in (11,23)]
        point = {}
        for key in ("win_rate", "eig_per_question"):
            if key == "win_rate":
                b = np.array([g["won"] for g in base])[indices].mean(axis=-1)
                f = np.array([[g["won"] for g in gs] for gs in final])[:,indices].mean(axis=-1)
            else:
                bq = np.array([g["questions"] for g in base])[indices].sum(axis=-1)
                fq = np.array([[g["questions"] for g in gs] for gs in final])[:,indices].sum(axis=-1)
                be = np.array([sum(g["question_eigs"]) for g in base])[indices].sum(axis=-1)
                fe = np.array([[sum(g["question_eigs"]) for g in gs] for gs in final])[:,indices].sum(axis=-1)
                b = np.divide(be, bq, out=np.full(bq.shape, np.nan), where=bq > 0)
                f = np.divide(fe, fq, out=np.full(fq.shape, np.nan), where=fq > 0)
            point[key] = f[seed_draw, np.arange(draws)].mean(axis=0) - b
        deltas.append(point)
    results = {}
    for name, selected in {
        "equal_cell_all": list(range(len(cells))),
        "noiseless_animals": [i for i,c in enumerate(cells) if c[0]=="animals" and c[2]==0],
        "noiseless_synthetic": [i for i,c in enumerate(cells) if c[0]=="synthetic" and c[2]==0],
    }.items():
        results[name] = {}
        for key in ("win_rate", "eig_per_question"):
            values = np.mean([deltas[i][key] for i in selected], axis=0)
            valid = values[np.isfinite(values)]
            results[name][key] = np.quantile(valid, [.025, .975]).tolist() if len(valid) else None
    return {"ci95_mean_A_endpoint_minus_raw":results,"seeds":[11,23],"draws":draws,
            "method":"Resample the two training seeds, then paired complete games within cells, sharing game draws across seeds and matching noise variants. Equal weight per cell; the base control is shared. Two seeds provide limited information about training variability."}


def main():
    primary = {seed: read_rows(ROOT / f"results/main_A{seed}/games.jsonl.gz") for seed in (11,23)}
    summaries = {seed: json.loads((ROOT / f"results/main_A{seed}/summary.json").read_text()) for seed in (11,23)}
    raw = [g for g in primary[11] if g["kind"] == "eval_base"]
    manifest=json.loads(gzip.decompress((ROOT/"experiments/main_A23_games.json.gz").read_bytes()))
    records={r["id"]:r for r in manifest["evaluation"]}
    raw_name_audits={}
    for seed,gs in primary.items():
        own=json.loads(gzip.decompress((ROOT/f"experiments/main_A{seed}_games.json.gz").read_bytes()))
        own_records={r["record"]["id"]:r["record"] for r in own["training"]}
        own_records.update({r["id"]:r for r in own["evaluation"]+own["development"]})
        raw_name_audits[str(seed)]={kind:audit_name_references([g for g in gs if g["kind"]==kind],own_records) for kind in ("train","eval_endpoint")}
    endpoints = {seed:[g for g in games if g["kind"] == "eval_endpoint"] for seed,games in primary.items()}
    suffix = auxiliary("suffix")
    hard = auxiliary("hard")
    cells = sorted({(g["domain"],g["n"],g["noise"]) for g in raw})
    rows = []
    changes = []
    for domain,n,noise in cells:
        subset = {seed:sorted([g for g in gs if (g["domain"],g["n"],g["noise"]) == (domain,n,noise)],key=lambda g:g["game_id"]) for seed,gs in endpoints.items()}
        delta,draws = paired_cell(subset[11],subset[23],seed=20261119+cells.index((domain,n,0)))
        changes.append(draws)
        rows.append({"domain":domain,"n":n,"noise":noise,"A11":metrics(subset[11]),"A23":metrics(subset[23]),"A23_minus_A11":delta,
                     "A11_stopping":unused_budget(subset[11]),"A23_stopping":unused_budget(subset[23])})
    noiseless_animal_indices=[i for i,r in enumerate(rows) if r["domain"]=="animals" and r["noise"]==0]
    headline={}
    for key in ("win_rate","eig_per_question"):
        draws=np.mean([changes[i][key] for i in noiseless_animal_indices],axis=0)
        headline[key]={"A11":float(np.mean([rows[i]["A11"][key] for i in noiseless_animal_indices])),
                       "A23":float(np.mean([rows[i]["A23"][key] for i in noiseless_animal_indices])),
                       "A23_minus_A11":float(np.mean([rows[i]["A23_minus_A11"][key]["final_minus_base"] for i in noiseless_animal_indices])),
                       "paired_games_ci95":np.quantile(draws,[.025,.975]).tolist()}
    suffix_rows=[]
    for domain,n,noise in cells:
        if domain != "synthetic": continue
        gs=sorted([g for g in suffix if g["n"]==n and g["noise"]==noise],key=lambda g:g["game_id"])
        strict=sorted([g for g in endpoints[23] if g["domain"]==domain and g["n"]==n and g["noise"]==noise],key=lambda g:g["game_id"])
        delta,_=paired_cell(strict,gs)
        mappings=Counter((m["identifier"],m["attribute"]) for g in gs for t in g["turns"] for m in t["suffix_mappings"])
        suffix_rows.append({"n":n,"noise":noise,"primary_A23":summarize(strict,bootstrap=10000),
                           "diagnostic_A23":summarize(gs,bootstrap=10000),"diagnostic_minus_primary":delta,
                           "mapped_identifiers":sum(mappings.values()),"distinct_identifier_mappings":len(mappings),
                           "mapped_questions":sum(g["mapped_questions"] for g in gs),
                           "most_common_mappings":[{"identifier":a,"attribute":b,"occurrences":count} for (a,b),count in mappings.most_common(3)]})
    hard_rows=[]
    for domain,n,noise in cells:
        gs={policy:sorted([g for g in hard if g["policy"]==policy and (g["domain"],g["n"],g["noise"])==(domain,n,noise)],key=lambda g:g["game_id"]) for policy in ("raw_base","A23_endpoint")}
        delta,_=paired_cell(gs["raw_base"],gs["A23_endpoint"])
        hard_rows.append({"domain":domain,"n":n,"noise":noise,**{p:metrics(g) for p,g in gs.items()},"endpoint_minus_base":delta})
    result={"A11_suffix_status":"not run: A11 checkpoint wasn't persisted, external uploads unavailable",
            "A11_hard_mode_status":"not run: A11 checkpoint wasn't persisted, external uploads unavailable",
            "noiseless_animal_replication":headline,"frozen_A11_vs_A23":rows,
            "hierarchical_seed_and_game_bootstrap":across_seed_intervals(raw,endpoints,cells),
            "synthetic_identifier_errors":{str(seed):s["transfer_identifier_audit"]["policies"]["eval_endpoint"] for seed,s in summaries.items()},
            "synthetic_identifier_AST_audit":{str(seed):identifier_forms(gs,records) for seed,gs in endpoints.items()},
            "post_hoc_raw_candidate_name_audits":raw_name_audits,
            "development":{str(seed):s["development"] for seed,s in summaries.items()},
            "guess_with_k_at_N128":[r for r in rows if r["n"]==128],
            "suffix_diagnostic_only":suffix_rows,"hard_mode_descriptive_only":hard_rows,
            "limitations":"Two A seeds; paired-game CIs describe these fitted endpoints. They are not a precise estimate of variation over training seeds. Hard mode has two games per cell and is descriptive. Suffix evaluation changes the environment parser and is excluded from all primary claims.",
            "B41_started":False}
    save_json(ROOT / "results/main_A23/replication_summary.json",result)
    print(json.dumps({"noiseless_animals":headline,"suffix_games":len(suffix),"hard_games":len(hard)},indent=2))


if __name__ == "__main__":
    main()
