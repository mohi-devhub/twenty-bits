"""Stopping measurements for fixed-policy, paired budget observations."""


def flags(game):
    limit = 2 * (game["n"] - 1).bit_length()
    state = game["guess_state"]
    ambiguous = bool(state and state["k_remaining"] > 1)
    return {
        "ambiguous_with_budget_left": ambiguous and game["questions"] < limit,
        "ambiguous_guess": ambiguous,
        "no_guess": state is None,
        "extra_ask_final": any(
            t["question_index"] == limit
            and not t["is_question"]
            and t["action"].startswith("ASK:")
            for t in game["turns"]
        ),
        "early_guess_win": bool(game["early_guess"] and game["won"]),
    }


def summarize(games):
    count = len(games)
    questions = sum(g["questions"] for g in games)
    wins = sum(g["won"] for g in games)
    indicators = [flags(g) for g in games]
    result = {
        "games": count,
        "wins": wins,
        "win_rate": wins / count,
        "questions": questions,
        "eig_per_question": sum(sum(g["question_eigs"]) for g in games) / questions
        if questions
        else None,
        "questions_per_win": sum(g["questions"] for g in games if g["won"]) / wins
        if wins
        else None,
        "invalid_questions": sum(g["invalid_count"] for g in games),
        "invalid_rate": sum(g["invalid_count"] for g in games) / questions
        if questions
        else None,
        "truncated_turns": sum(g["truncation_count"] for g in games),
        "enumeration_questions": sum(g["enumeration_count"] for g in games),
    }
    for key in indicators[0]:
        result[key + "_games"] = sum(row[key] for row in indicators)
        result[key + "_rate"] = result[key + "_games"] / count
    result["early_guess_games"] = sum(g["early_guess"] for g in games)
    result["early_guess_win_fraction"] = (
        result["early_guess_win_games"] / result["early_guess_games"]
        if result["early_guess_games"]
        else None
    )
    return result
