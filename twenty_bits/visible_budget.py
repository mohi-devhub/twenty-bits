"""Public question counter for the labelled evaluation-only follow-up."""

from .candidate_feedback import candidate_messages

PROMPT_VERSION = "visible-budget-v1"


def budget_text(remaining: int, limit: int) -> str:
    text = f"Questions left: {remaining} of {limit}"
    if remaining == 0:
        text += "\nNo questions left. You must GUESS now."
    return text


def visible_budget_messages(
    record: dict, turns: list[dict] | None = None
) -> list[dict]:
    public = candidate_messages(record, turns)
    limit = 2 * (len(record["world"]["names"]) - 1).bit_length()
    public[1]["content"] += "\n" + budget_text(limit, limit)
    used = 0
    for index, turn in enumerate(turns or []):
        used += int(turn["is_question"])
        public[3 + 2 * index]["content"] += "\n" + budget_text(limit - used, limit)
    return public
