"""Exact finite-world entropy, likelihoods, posterior updates, and information gain."""

import numpy as np


def entropy(probabilities: np.ndarray) -> float:
    p = np.asarray(probabilities, dtype=float)
    positive = p[p > 0]
    return float(-np.sum(positive * np.log2(positive)))


def binary_entropy(q):
    q = np.asarray(q, dtype=float)
    clipped = np.clip(q, 1e-300, 1 - 1e-16)
    result = -q * np.log2(clipped) - (1 - q) * np.log2(1 - clipped)
    return np.where((q == 0) | (q == 1), 0.0, result)


def expected_gain(posterior: np.ndarray, masks: np.ndarray, noise: float):
    mass = np.asarray(masks, dtype=float) @ posterior
    return binary_entropy(noise + (1 - 2 * noise) * mass) - binary_entropy(noise)


def update(
    posterior: np.ndarray, mask: np.ndarray, answer: bool, noise: float
) -> np.ndarray:
    likelihood = np.where(mask == answer, 1 - noise, noise)
    result = posterior * likelihood
    total = float(result.sum())
    if total <= 0:
        raise ValueError(
            "The answer has zero probability under this noiseless history."
        )
    return result / total
