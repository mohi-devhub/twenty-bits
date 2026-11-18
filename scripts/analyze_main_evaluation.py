"""Paired frozen-cell estimates, stopping counts and equal-cell comparisons."""

import math
import numpy as np
from scripts.run_baselines import summarize
from twenty_bits.guess_metrics import guess_summary


def paired_cell(base, final, *, seed=20261118, draws=10000):
    assert [g["game_id"] for g in base] == [g["game_id"] for g in final]
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(base), size=(draws, len(base)))

    def stats(gs, indices):
        win = np.array([g["won"] for g in gs], dtype=float)
        q = np.array([g["questions"] for g in gs], dtype=float)
        eig = np.array([sum(g["question_eigs"]) for g in gs])
        sums = q[indices].sum(axis=-1)
        wins = win[indices].sum(axis=-1)
        return {
            "win_rate": win[indices].mean(axis=-1),
            "eig_per_question": np.divide(
                eig[indices].sum(axis=-1),
                sums,
                out=np.full(np.shape(sums), np.nan),
                where=sums > 0,
            ),
            "questions_per_win": np.divide(
                (q * win)[indices].sum(axis=-1),
                wins,
                out=np.full(np.shape(wins), np.nan),
                where=wins > 0,
            ),
        }

    b, f = stats(base, idx), stats(final, idx)
    bp, fp = stats(base, np.arange(len(base))), stats(final, np.arange(len(final)))
    result = {}
    deltas = {}
    for key in b:
        changes = f[key] - b[key]
        valid = changes[np.isfinite(changes)]
        deltas[key] = changes
        result[key] = {
            "final_minus_base": float(fp[key] - bp[key])
            if np.isfinite(fp[key] - bp[key])
            else None,
            "ci95": np.quantile(valid, [0.025, 0.975]).tolist() if len(valid) else None,
            "defined_bootstrap_draws": len(valid),
        }
    d = [
        int(f["won"]) - int(b["won"])
        for b, f in zip(base, final)
        if b["won"] != f["won"]
    ]
    n = len(d)
    extreme = min(sum(x > 0 for x in d), sum(x < 0 for x in d))
    result["exact_paired_win_p"] = (
        min(1.0, 2 * sum(math.comb(n, i) for i in range(extreme + 1)) / (2**n))
        if n
        else 1.0
    )
    changes = np.array(
        [
            f["eig_per_question"] - b["eig_per_question"]
            for b, f in zip(base, final)
            if b["eig_per_question"] is not None and f["eig_per_question"] is not None
        ]
    )
    if len(changes):
        permuted = np.abs(
            (rng.choice([-1, 1], (draws, len(changes))) * changes).mean(axis=1)
        )
        result["per_game_eig_permutation"] = {
            "pairs": len(changes),
            "two_sided_p": float(
                (1 + sum(permuted >= abs(changes.mean()) - 1e-12)) / (draws + 1)
            ),
            "draws": draws,
            "method": "Paired random sign permutation of per-game EIG, secondary to ratio-of-sums EIG.",
        }
    return result, deltas


def wilson(wins, n):
    z = 1.959963984540054
    center = (wins / n + z * z / (2 * n)) / (1 + z * z / n)
    half = (
        z
        * math.sqrt(wins / n * (1 - wins / n) / n + z * z / (4 * n * n))
        / (1 + z * z / n)
    )
    return [max(0, center - half), min(1, center + half)]


def frozen_comparison(games, records):
    from scripts.summarize_phase2 import extra_metrics

    cells = sorted({(r["domain"], r["n"], r["noise"]) for r in records})
    rows = []
    delta_draws = []
    for domain, n, noise in cells:
        pair = {
            kind: sorted(
                [
                    g
                    for g in games
                    if g["kind"] == kind
                    and (g["domain"], g["n"], g["noise"]) == (domain, n, noise)
                ],
                key=lambda g: g["game_id"],
            )
            for kind in ("eval_base", "eval_endpoint")
        }
        assert all(len(gs) == 28 for gs in pair.values())
        metrics = {}
        for kind, gs in pair.items():
            wins = sum(g["won"] for g in gs)
            metrics[kind] = {
                **summarize(gs, bootstrap=10000),
                **extra_metrics(gs),
                "guess_with_k_remaining": guess_summary(gs),
                "win_rate_wilson_ci95": wilson(wins, len(gs)),
            }
        # The same draw indices across noise versions preserve their pairing.
        paired, draws = paired_cell(
            pair["eval_base"],
            pair["eval_endpoint"],
            seed=20261118 + cells.index((domain, n, 0)),
        )
        delta_draws.append(draws)
        rows.append(
            {
                "domain": domain,
                "n": n,
                "noise": noise,
                "base": metrics["eval_base"],
                "endpoint": metrics["eval_endpoint"],
                "paired_final_minus_base": paired,
            }
        )
    headline = {}
    for key in ("win_rate", "eig_per_question"):
        points = [r["paired_final_minus_base"][key]["final_minus_base"] for r in rows]
        changes = np.mean([d[key] for d in delta_draws], axis=0)
        valid = changes[np.isfinite(changes)]
        base = [r["base"][key] for r in rows]
        final = [r["endpoint"][key] for r in rows]
        headline[key] = {
            "final_minus_base": float(np.mean(points))
            if all(p is not None for p in points)
            else None,
            "ci95": np.quantile(valid, [0.025, 0.975]).tolist() if len(valid) else None,
            "defined_bootstrap_draws": len(valid),
            "base": float(np.mean(base)) if all(p is not None for p in base) else None,
            "endpoint": float(np.mean(final))
            if all(p is not None for p in final)
            else None,
        }
    return {
        "cells": rows,
        "equal_cell_headline": headline,
        "method": "10,000 complete-game bootstrap draws within each cell, paired across policies and noise versions. Equal weight per cell. One A training seed; no between-seed CI. Per-cell secondary p-values are unadjusted and all are reported.",
    }
