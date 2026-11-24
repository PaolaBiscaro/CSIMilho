"""Small deterministic statistical primitives used by analytical tools.

No model selects or calculates these results.  The helpers deliberately use
few-assumption paired methods because FarmLab currently has small samples and
does not document normality.  Time-series results remain exploratory because
successive dates may be autocorrelated.
"""

from dataclasses import dataclass
from math import comb, isfinite
from statistics import median
from typing import Literal


@dataclass(frozen=True)
class TestSelection:
    method: Literal["paired_sign_test", "descriptive_only"]
    minimum_pairs: int
    reason: str
    inference_scope: Literal["confirmatory", "exploratory"]
    multiplicity_correction: Literal["holm", "none"]


def select_paired_continuous_test(
    pair_count: int,
    *,
    repeated_time: bool = False,
    multiple_metrics: bool = False,
) -> TestSelection:
    """Choose the only currently validated paired continuous-data design."""
    if pair_count < 5:
        return TestSelection(
            method="descriptive_only",
            minimum_pairs=5,
            reason="Menos de cinco pares válidos; o resultado deve permanecer descritivo.",
            inference_scope="exploratory",
            multiplicity_correction="holm" if multiple_metrics else "none",
        )
    temporal_note = (
        " As datas sucessivas podem ser autocorrelacionadas; a inferência é exploratória."
        if repeated_time
        else ""
    )
    return TestSelection(
        method="paired_sign_test",
        minimum_pairs=5,
        reason=(
            "Teste exato dos sinais: os valores estão pareados e não há pressuposto documentado "
            f"de normalidade.{temporal_note}"
        ),
        inference_scope="exploratory" if repeated_time else "confirmatory",
        multiplicity_correction="holm" if multiple_metrics else "none",
    )


def _average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and ordered[end][1] == ordered[cursor][1]:
            end += 1
        average = ((cursor + 1) + end) / 2
        for position in range(cursor, end):
            ranks[ordered[position][0]] = average
        cursor = end
    return ranks


def _median_distribution_free_interval(values: list[float], alpha: float) -> tuple[float, float] | None:
    """Return an exact order-statistic interval when finite coverage exists."""
    ordered = sorted(values)
    n = len(ordered)
    selected_k = None
    for k in range(1, n // 2 + 1):
        lower_tail = sum(comb(n, index) for index in range(k)) / (2**n)
        if lower_tail <= alpha / 2:
            selected_k = k
        else:
            break
    if selected_k is None:
        return None
    return ordered[selected_k - 1], ordered[n - selected_k]


def paired_sign_statistics(differences: list[float], *, alpha: float = 0.05) -> dict:
    """Exact two-sided sign test plus matched-pairs rank-biserial effect."""
    finite = [float(value) for value in differences if isfinite(value)]
    nonzero = [value for value in finite if abs(value) > 1e-12]
    selection = select_paired_continuous_test(len(nonzero))
    if selection.method == "descriptive_only":
        raise ValueError(selection.reason)

    positives = sum(value > 0 for value in nonzero)
    negatives = len(nonzero) - positives
    extreme = min(positives, negatives)
    p_value = min(1.0, 2 * sum(comb(len(nonzero), index) for index in range(extreme + 1)) / (2 ** len(nonzero)))

    ranks = _average_ranks([abs(value) for value in nonzero])
    positive_ranks = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value > 0)
    negative_ranks = sum(rank for rank, value in zip(ranks, nonzero, strict=True) if value < 0)
    rank_total = positive_ranks + negative_ranks
    effect = (positive_ranks - negative_ranks) / rank_total
    interval = _median_distribution_free_interval(nonzero, alpha)
    return {
        "pair_count": len(finite),
        "nonzero_pairs": len(nonzero),
        "positive_pairs": positives,
        "negative_pairs": negatives,
        "median_difference": float(median(nonzero)),
        "confidence_level": 1 - alpha,
        "median_ci_low": None if interval is None else float(interval[0]),
        "median_ci_high": None if interval is None else float(interval[1]),
        "p_value": float(p_value),
        "rank_biserial": float(effect),
        "significant": p_value <= alpha,
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm family-wise adjustment, preserving the original order."""
    if any(not isfinite(value) or not 0 <= value <= 1 for value in p_values):
        raise ValueError("p-valores devem ser finitos e estar entre zero e um.")
    count = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * count
    running = 0.0
    for rank, (original_index, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * value))
        adjusted[original_index] = running
    return adjusted
