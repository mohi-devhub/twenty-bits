"""Stopping behavior measured from public state, without changing the game."""

from .candidate_feedback import feedback

BINS = ("1", "2", "3", "4+")


def bucket(k):
    if k < 1:
        raise ValueError("A guess needs at least one possible candidate.")
    return str(k) if k < 4 else "4+"


def guess_state(game, record):
    guesses = [t for t in game["turns"] if t["action"].startswith("GUESS: ")]
    if not guesses:
        return None
    if len(guesses) != 1:
        raise ValueError("A terminal-guess game cannot have multiple guesses.")
    turn = guesses[0]
    posterior = turn["posterior_before"]
    public = feedback(record, posterior)["candidates"]
    name = turn["action"][7:].strip()
    names = record["world"]["names"]
    k = len(public)
    return {
        "k_remaining": k,
        "bin": bucket(k),
        "won": turn["answer"] == "WIN",
        "definition": "exact_support"
        if record["noise"] == 0
        else "displayed_threshold_plus_top",
        "positive_posterior_support": sum(p > 0 for p in posterior),
        "guessed_in_displayed_candidates": name in public,
        "guessed_in_table": name in names,
        "guessed_posterior_probability": posterior[names.index(name)]
        if name in names
        else 0.0,
    }


def guess_summary(games):
    if not games:
        raise ValueError("Stopping summaries need games.")
    guesses = [g["guess_state"] for g in games if g["guess_state"] is not None]
    bins = {}
    support_bins = {}
    for label in BINS:
        subset = [g for g in guesses if g["bin"] == label]
        count, wins = len(subset), sum(g["won"] for g in subset)
        bins[label] = {
            "guesses": count,
            "wins": wins,
            "guesses_per_game": count / len(games),
            "share_of_guesses": count / len(guesses) if guesses else None,
            "win_rate_when_guessed": wins / count if count else None,
        }
        raw = [g for g in guesses if bucket(g["positive_posterior_support"]) == label]
        support_bins[label] = {"guesses": len(raw), "wins": sum(g["won"] for g in raw)}
    ambiguous = [g for g in guesses if g["k_remaining"] > 1]
    return {
        "games": len(games),
        "guesses": len(guesses),
        "no_guess_games": len(games) - len(guesses),
        "ambiguous_guesses": len(ambiguous),
        "ambiguous_guess_wins": sum(g["won"] for g in ambiguous),
        "ambiguous_guesses_per_game": len(ambiguous) / len(games),
        "bins": bins,
        "positive_posterior_support_bins": support_bins,
        "guesses_outside_displayed_candidates": sum(
            not g["guessed_in_displayed_candidates"] for g in guesses
        ),
        "mean_guessed_posterior_probability": sum(
            g["guessed_posterior_probability"] for g in guesses
        )
        / len(guesses)
        if guesses
        else None,
    }
