"""Stable public table prefix. Targets and posterior state never enter prompts."""

from __future__ import annotations
from functools import cache
import json
from transformers import AutoTokenizer
from .worlds import ROOT, World

RULES = """You play Twenty Questions. Identify one hidden item from the table. After each item name, the listed column codes are true; every omitted code is false. Use full attribute names from the code=name mapping in questions. The table defines truth, even if your world knowledge differs. Output exactly one line: ASK: <Boolean expression> or GUESS: <exact item name>. Expressions use attribute identifiers, AND, OR, NOT, parentheses, and item == <item name>. Quote names containing spaces with JSON double quotes. A wrong guess ends the game. An invalid question costs a question. You may use any legal Boolean expression, including lists of item equalities. Do not explain or show reasoning."""


def prefix(world: World) -> str:
    def code(index: int) -> str:
        result = ""
        while True:
            result = chr(97 + index % 26) + result
            index = index // 26 - 1
            if index < 0:
                return result

    codes = [code(i) for i in range(len(world.attributes))]
    header = (
        "DOMAIN "
        + world.domain
        + "\nATTRIBUTES code=name\n"
        + ",".join(f"{c}={a}" for c, a in zip(codes, world.attributes))
        + "\nTABLE name|true column codes\n"
    )
    rows = "\n".join(
        name + "|" + ",".join(c for c, x in zip(codes, row) if x)
        for name, row in zip(world.names, world.rows)
    )
    return RULES + "\n" + header + rows + "\nEND TABLE\n"


def messages(record: dict, turns: list[dict] | None = None) -> list[dict]:
    world = World.from_dict(record["world"])
    # Settings follow the table so the table prefix matches across noise modes.
    limit = 2 * (len(world.names) - 1).bit_length()
    settings = f"Answer flip probability: {record['noise']:.2f}, independently each question. Maximum questions: {limit}. After the last answer, make one final guess; another question loses. Begin."
    result = [
        {"role": "system", "content": prefix(world)},
        {"role": "user", "content": settings},
    ]
    for turn in turns or []:
        result.extend(
            [
                {
                    "role": "assistant",
                    "content": turn.get("raw_action", turn["action"]),
                },
                {"role": "user", "content": turn["answer"]},
            ]
        )
    return result


@cache
def get_tokenizer(model: str = "Qwen/Qwen3-8B"):
    manifest = json.loads((ROOT / "research/tokenizers.json").read_text())
    entry = next(x for x in manifest if x["model"] == model)
    local = ROOT / entry["local_cache"]
    return AutoTokenizer.from_pretrained(
        local if local.exists() else model,
        revision=None if local.exists() else entry["revision"],
    )


def prompt_ids(
    record: dict, turns: list[dict] | None = None, model: str = "Qwen/Qwen3-8B"
) -> list[int]:
    tokenizer = get_tokenizer(model)
    return tokenizer.apply_chat_template(
        messages(record, turns),
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
    )
