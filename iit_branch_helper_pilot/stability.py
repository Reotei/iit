"""
stability.py — Step B: does a recommendation hold up if the weights are a bit off?

Default weights are placeholders (until survey question 31), and no student can
state their weights precisely. So we re-run the ranking many times, each time
nudging every weight up or down a little at random, and count how often each
option stays in the top N.

Method (see the v2.2 plan):
  1. Every factor score (0-1) is computed ONCE, in scoring.py. Only weights change.
  2. In each run, every weight is multiplied by a random number between
     (1 - max_change) and (1 + max_change). A weight of 0 stays 0: the student said
     "don't care".
  3. Re-score with the SAME formula as scoring.py:
        score = sum(weight x factor score) / sum(weights of factors used) x 100
     Factors with no data (score None) are left out of both sums, exactly as in
     scoring.py, so no extra normalisation is needed.
  4. Sort by score; exact ties are broken by how sought-after the program is,
     exactly as in scoring.py. Record which options are in the top N.
  5. share_in_top_n = times_in_top_n / number_of_runs.

A fixed random seed makes the labels reproducible: same inputs, same labels.
"""

import numpy as np
import pandas as pd

from scoring import FACTOR_NAMES


STABLE_SHARE = 0.80
DEPENDS_SHARE = 0.40

LABEL_STABLE = "Stable pick"
LABEL_DEPENDS = "Depends on your weights"
LABEL_FRAGILE = "Fragile"


def build_score_matrices(ranked_options):
    """
    Two tables of numbers, one row per option and one column per factor:
      score_matrix - the factor score (0-1), or 0 where the factor is not used
      used_matrix  - 1 where the factor is used for this option, 0 where not
    """
    number_of_options = len(ranked_options)
    number_of_factors = len(FACTOR_NAMES)
    score_matrix = np.zeros((number_of_options, number_of_factors))
    used_matrix = np.zeros((number_of_options, number_of_factors))

    row_position = 0
    for _, option in ranked_options.iterrows():
        factor_scores = option["factor_scores"]
        for column_position in range(number_of_factors):
            factor_name = FACTOR_NAMES[column_position]
            factor_score = factor_scores.get(factor_name, None)
            if factor_score is not None:
                score_matrix[row_position, column_position] = factor_score
                used_matrix[row_position, column_position] = 1.0
        row_position = row_position + 1
    return score_matrix, used_matrix


def scores_for_weights(score_matrix, used_matrix, weight_vector):
    """The scoring.py formula, for every option at once."""
    weighted_totals = (score_matrix * weight_vector).sum(axis=1)
    weight_with_data = (used_matrix * weight_vector).sum(axis=1)
    scores = np.full(len(weighted_totals), -1.0)  # -1 = nothing to score, sorts last
    has_weight = weight_with_data > 0
    scores[has_weight] = 100.0 * weighted_totals[has_weight] / weight_with_data[has_weight]
    return scores


def top_positions(scores, tie_break_values, how_many):
    """
    Positions of the best `how_many` options: highest score first, exact ties
    (to 6 decimals, as in scoring.py) broken by the higher tie-break value.
    np.lexsort sorts by the LAST key first, so the score goes last.
    """
    rounded_scores = np.round(scores, 6)
    order = np.lexsort((-tie_break_values, -rounded_scores))
    return order[:how_many]


def label_for(share, base_rank, times_in_top, top_n):
    if share >= STABLE_SHARE:
        return LABEL_STABLE
    if share >= DEPENDS_SHARE:
        return LABEL_DEPENDS
    # Only worth calling "Fragile" if it was in the top N at least once
    if base_rank <= top_n or times_in_top > 0:
        return LABEL_FRAGILE
    return ""


def check_stability(ranked_options, student_weights, number_of_runs=500, max_change=0.20,
                    top_n=10, random_seed=42):
    """
    ranked_options:  the table from scoring.rank_options (already sorted, with
                     "factor_scores", "tie_break_demand" and "preference_rank").
    student_weights: {factor_name: weight}, as used for the base ranking.
    Returns a table: option_id, times_in_top_n, share_in_top_n, stability_label.
    """
    number_of_options = len(ranked_options)
    empty_result = pd.DataFrame(columns=["option_id", "times_in_top_n", "share_in_top_n", "stability_label"])
    if number_of_options == 0:
        return empty_result

    effective_top_n = top_n
    if number_of_options < top_n:
        effective_top_n = number_of_options

    score_matrix, used_matrix = build_score_matrices(ranked_options)
    tie_break_values = ranked_options["tie_break_demand"].to_numpy(dtype=float)

    base_weight_list = []
    for factor_name in FACTOR_NAMES:
        base_weight_list.append(student_weights.get(factor_name, 0.0))
    base_weights = np.array(base_weight_list, dtype=float)

    random_generator = np.random.default_rng(random_seed)
    times_in_top = np.zeros(number_of_options, dtype=int)

    for run_number in range(number_of_runs):
        multipliers = random_generator.uniform(1.0 - max_change, 1.0 + max_change, size=len(base_weights))
        run_weights = base_weights * multipliers   # a weight of 0 stays 0
        run_scores = scores_for_weights(score_matrix, used_matrix, run_weights)
        best_positions = top_positions(run_scores, tie_break_values, effective_top_n)
        for position in best_positions:
            times_in_top[position] = times_in_top[position] + 1

    result_rows = []
    row_position = 0
    for _, option in ranked_options.iterrows():
        times_value = int(times_in_top[row_position])
        share_value = times_value / number_of_runs
        base_rank = int(option["preference_rank"])
        result_rows.append({
            "option_id": base_rank,
            "times_in_top_n": times_value,
            "share_in_top_n": share_value,
            "stability_label": label_for(share_value, base_rank, times_value, effective_top_n),
        })
        row_position = row_position + 1
    return pd.DataFrame(result_rows)
