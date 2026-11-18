"""The authorized prompt-only probe. Frozen Phase 2 prompts stay unchanged."""

import random

from .prompts import messages
from .worlds import World, seed_for, training_game

PROMPT_VERSION = "grammar-examples-v1"
PROBE_SEED = 20261118

RULES = """You are the guesser in a yes/no identification game. One of the table's items is hidden. Identify it using answers to Boolean questions, then make a final guess.

Reply with ONE action on ONE line. No explanation, table, code block, or extra text.
To ask: ASK: <expression>
To finish: GUESS: <exact item name from TABLE>
A guess ends the game. It wins only when it names the hidden item. You must make a guess after the last allowed answer.

Each expression is a Boolean test applied to ONE item. An attribute identifier is already a complete expression. AND, OR, NOT and parentheses combine expressions. Item equality is also legal: item == "<exact item name>". Any legal expression, including a list of item equalities, is allowed. Unknown attributes or item names are invalid. An invalid question consumes a question and returns INVALID.

Read ATTRIBUTES as code=full_name. The short codes in TABLE are a compact storage notation, not expression identifiers. In an ASK, copy the full_name to the RIGHT of =. An item has an attribute when its row lists that attribute's code; every omitted code is false. The table defines truth. Real-world knowledge does not override it.
"""


def probe_records() -> list[dict]:
    return [
        training_game(n, index, seed=PROBE_SEED, noise=0)
        for n in (8, 16)
        for index in range(16)
    ]


def prompt_examples(world: World) -> list[str]:
    # Selection never sees the target, posterior, column values, or split quality.
    rng = random.Random(seed_for(PROMPT_VERSION, world.attributes, world.names))
    a, b, c = rng.choices(world.attributes, k=3)
    return [f"ASK: {a}", f"ASK: NOT {b}", f"ASK: ({a} AND {c})"]


def probe_messages(record: dict, turns: list[dict] | None = None) -> list[dict]:
    public = messages(record, turns)
    world = World.from_dict(record["world"])
    table = public[0]["content"].split("\nDOMAIN ", 1)[1]
    examples = prompt_examples(world)
    worked = (
        "\nGRAMMAR EXAMPLES, selected randomly, not moves already played:\n"
        + examples[0]
        + "\nThis tests that attribute on the hidden item's row.\n"
        + examples[1]
        + "\nThis tests the negation of that attribute.\n"
        + examples[2]
        + "\nThis tests whether both named attributes are true.\n"
        + "These examples show syntax only. Select your own question. Never copy column codes into an expression.\n"
    )
    public[0]["content"] = RULES + worked + "\nDOMAIN " + table
    return public
