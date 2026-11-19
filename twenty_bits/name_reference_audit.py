"""Post-hoc candidate-name references, including malformed identity questions."""

from collections import Counter
import json

from .predicates import LEX


def referenced_names(body, names):
    """Read exact lexical names without accepting or repairing the predicate."""
    tokens=[m.group(1) for m in LEX.finditer(body)]
    found=set()
    for index,token in enumerate(tokens):
        if token=="item" and index+1<len(tokens) and tokens[index+1]=="==":
            continue
        if token.startswith('"'):
            try:
                token=json.loads(token)
            except ValueError:
                continue
        if token in names:
            found.add(token)
    return found


def audit_name_references(games, records):
    counts=Counter();examples=[]
    for game in sorted(games,key=lambda g:(g["kind"],g["update"],g["game_id"],g.get("member") or 0)):
        names=set(records[game["game_id"]]["world"]["names"])
        previous_bare=None
        for turn in game["turns"]:
            if not turn["is_question"]:
                continue
            counts["counted_questions"]+=1
            action=turn["raw_action"].strip()
            body=action[4:].strip() if action.startswith("ASK:") else ""
            found=referenced_names(body,names)
            if not found:
                previous_bare=None
                continue
            counts["questions_with_exact_candidate_name_references"]+=1
            counts["invalid_questions_with_name_references"]+=turn["invalid"]
            counts["name_list_questions"]+=len(found)>=2
            counts["invalid_name_list_questions"]+=len(found)>=2 and turn["invalid"]
            counts["lists_at_least_quarter_original_N"]+=len(found)>=2 and len(found)>=game["n"]/4
            bare=body if body in names else None
            if bare:
                support=sum(p>0 for p in turn["posterior_before"])
                counts["bare_candidate_name_questions"]+=1
                counts["invalid_bare_candidate_name_questions"]+=turn["invalid"]
                counts["bare_candidate_name_at_singleton"]+=support==1
                counts["consecutive_different_bare_names"]+=previous_bare is not None and previous_bare!=bare
            previous_bare=bare
            if turn["invalid"] and len(examples)<3:
                examples.append({"game_id":game["game_id"],"update":game["update"],
                    "raw_action":turn["raw_action"],"distinct_candidate_names":len(found),
                    "posterior_support":sum(p>0 for p in turn["posterior_before"]),"error":turn.get("error")})
    return {"counts":dict(counts),"examples":examples,
        "definition":"Post-hoc raw exact-name reference audit; identifiers and quoted names must match a candidate literally. It includes malformed ASK bodies, which are still INVALID with zero EIG. A raw name reference is not proof of intended enumeration. Legal item-equality enumeration remains the unchanged primary metric.",
        "primary_scoring_changed":False}
