"""Replay the exact public prompts before A23's post-budget ASK attempts."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.worlds import ROOT


def main():
    manifest = json.loads(
        gzip.decompress((ROOT / "experiments/main_A23_games.json.gz").read_bytes())
    )
    records = {row["record"]["id"]: row["record"] for row in manifest["training"]}
    config = json.loads((ROOT / "experiments/main_A23.json").read_text())
    rendering = Rendering(config["primary_model"], config)
    counts = Counter()
    cases = []
    for line in gzip.open(ROOT / "results/main_A23/games.jsonl.gz", "rt"):
        game = json.loads(line)
        if game["kind"] != "train":
            continue
        record = records[game["game_id"]]
        questions = 0
        limit = 2 * (record["n"] - 1).bit_length()
        for index, turn in enumerate(game["turns"]):
            if questions == limit and turn["raw_action"].startswith("ASK:"):
                public = candidate_messages(record, game["turns"][:index])
                prompt = rendering.prompt(public).to_ints()
                assert prompt == game["trajectory"][index]["ob"]
                assert turn["format_error"] and not turn["is_question"]
                initial = public[1]["content"]
                latest = public[-1]["content"]
                assert f"Maximum questions: {limit}." in initial
                # The response is exactly answer plus public candidate feedback.
                assert latest.startswith(("YES\n", "NO\n", "INVALID\n"))
                assert "Maximum questions:" not in latest
                assert "questions remaining" not in latest.lower()
                assert "questions left" not in latest.lower()
                assert "final guess" not in latest.lower()
                counts[str(record["n"])] += 1
                cases.append(
                    {
                        "game_id": game["game_id"],
                        "update": game["update"],
                        "turn": index,
                        "maximum_questions": limit,
                        "questions_used": questions,
                        "initial_settings": initial,
                        "latest_environment_message": latest,
                        "prompt_tokens_sha256": hashlib.sha256(
                            json.dumps(prompt).encode()
                        ).hexdigest(),
                    }
                )
            questions += int(turn["is_question"])
    assert len(cases) == 110
    result = {
        "service_calls": 0,
        "protocol_changed": False,
        "native_prompt_parity_cases": len(cases),
        "post_budget_ASK_actions": len(cases),
        "fixed_maximum_stated_in_history": len(cases),
        "fixed_maximum_absent_from_history": 0,
        "per_turn_remaining_count_stated": 0,
        "per_turn_remaining_count_not_stated": len(cases),
        "explicit_exhaustion_notice_before_action": 0,
        "by_N": dict(sorted(counts.items(), key=lambda row: int(row[0]))),
        "interpretation": "The initial user settings state the fixed maximum and final-guess rule. Each later user message contains YES/NO/INVALID plus candidate feedback, with no used/remaining counter or exhaustion notice. All 110 attempts had the maximum in history; none had an explicit per-turn remaining budget. The model could infer usage from played actions in history. No prompt was changed.",
        "cases": cases,
    }
    path = ROOT / "research/A23_budget_visibility.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Question-budget visibility audit",
        "",
        result["interpretation"],
        "",
        "At N=128 the initial user settings are exactly:",
        "",
        "```text",
        "Answer flip probability: 0.00, independently each question. Maximum questions: 14. After the last answer, make one final guess; another question loses. Begin.",
        "```",
        "",
        "The rules also say: `You must make a guess after the last allowed answer.`",
        "",
        "| Before the 110 post-budget ASK actions | Stated | Not stated |",
        "| --- | ---: | ---: |",
        "| Fixed maximum in conversation history | 110 | 0 |",
        "| Current remaining question count | 0 | 110 |",
        "| Explicit budget-exhausted notice | 0 | 110 |",
        "",
        "The categories overlap: a fixed maximum was visible in every case, while a dynamic remaining count was absent in every case. All 110 native prompt token sequences match the saved rollout inputs. This audit changes neither prompts nor scores. It does not establish why a model kept asking.",
        "",
        "[Every case and exact latest feedback](A23_budget_visibility.json).",
        "",
    ]
    (ROOT / "research/BUDGET_VISIBILITY.md").write_text("\n".join(lines))
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    main()
