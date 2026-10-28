"""
test_v22.py — tests for the must-have filter (Step A) and stability check (Step B).

Run:  python test_v22.py
Each test prints PASS or raises an AssertionError with what went wrong.
"""

import pandas as pd

from loader import load_all_closing_ranks
from feasibility import feasibility_for_student
from scoring import (load_institute_table, build_demand_table, prepare_options,
                     rank_options, ALL_BRANCH_GROUPS)
from musthaves import apply_must_haves, FEES_UNKNOWN_FLAG


closing_ranks = load_all_closing_ranks()
institutes = load_institute_table()
demand = build_demand_table(closing_ranks)

# Rank 1 sees every program, including the Abu Dhabi campus (unknown fees)
feasibility_air1 = feasibility_for_student(closing_ranks, "OPEN", False, False, crl_rank=1)
options_air1 = prepare_options(feasibility_air1, institutes, demand)
student_open = {"category": "OPEN", "is_pwd": False, "income_band": "Above Rs 5 lakh",
                "interest_ratings": {group_name: 3 for group_name in ALL_BRANCH_GROUPS}}


# ---------------------------------------------------------------------------
# Step A tests
# ---------------------------------------------------------------------------
def test_all_rules_off_removes_nothing():
    kept, removed = apply_must_haves(options_air1, {}, student_open)
    assert len(removed) == 0, "expected nothing removed, got " + str(len(removed))
    assert len(kept) == len(options_air1)

    rules_switched_off = {"max_tuition_per_year": None, "allowed_regions": [],
                          "exclude_five_year": False, "excluded_groups": []}
    kept, removed = apply_must_haves(options_air1, rules_switched_off, student_open)
    assert len(removed) == 0
    print("PASS  A1 all rules off -> nothing removed (" + str(len(kept)) + " kept)")


def test_fee_cap_below_every_fee_keeps_only_unknown_fee_rows():
    kept, removed = apply_must_haves(options_air1, {"max_tuition_per_year": 1000}, student_open)
    abu_dhabi_count = int(options_air1["is_abu_dhabi"].sum())
    assert abu_dhabi_count > 0, "test needs at least one Abu Dhabi option"
    assert len(kept) == abu_dhabi_count, "only unknown-fee rows should remain"
    for _, row in kept.iterrows():
        assert row["is_abu_dhabi"] == True
        assert FEES_UNKNOWN_FLAG in row["must_have_flags"]
    first_reason = removed["removed_reason"].iloc[0]
    assert "above your limit" in first_reason, first_reason
    print("PASS  A2 fee cap below every fee -> " + str(len(removed)) + " removed, "
          + str(len(kept)) + " unknown-fee rows kept and flagged")
    print("      example reason: " + first_reason)


def test_row_failing_two_rules_shows_both_reasons():
    rules = {"exclude_five_year": True, "allowed_regions": ["South"]}
    kept, removed = apply_must_haves(options_air1, rules, student_open)
    five_year_outside_south = removed[(removed["duration_years"] >= 5) & (removed["region"] != "South")]
    assert len(five_year_outside_south) > 0
    reason_text = five_year_outside_south["removed_reason"].iloc[0]
    assert "region" in reason_text and "year program" in reason_text, reason_text
    for _, row in kept.iterrows():
        assert row["duration_years"] <= 4 and row["region"] == "South"
    print("PASS  A3 a row failing two rules lists both reasons:")
    print("      " + reason_text)


def test_rank_options_filters_before_scoring():
    rules = {"excluded_groups": ["Computing"]}
    ranked, unrated, warnings, removed = rank_options(feasibility_air1, institutes, student_open,
                                                      demand_table=demand, must_haves=rules)
    assert (ranked["branch_group"] == "Computing").sum() == 0
    assert (removed["branch_group"] == "Computing").sum() == len(removed)
    print("PASS  A4 rank_options: excluded group removed before scoring ("
          + str(len(removed)) + " removed, " + str(len(ranked)) + " scored)")


# ---------------------------------------------------------------------------
# Step B tests
# ---------------------------------------------------------------------------
import time
from scoring import DEFAULT_WEIGHTS, FACTOR_NAMES
from stability import check_stability, LABEL_STABLE


def test_equal_scores_follow_tie_break():
    same_scores = {}
    for factor_name in FACTOR_NAMES:
        same_scores[factor_name] = None
    same_scores["interest"] = 0.75
    same_scores["institute_quality"] = 0.5
    two_options = pd.DataFrame({
        "preference_rank": [1, 2],
        "factor_scores": [dict(same_scores), dict(same_scores)],
        "tie_break_demand": [0.9, 0.3],   # option 1 is more sought-after
    })
    result = check_stability(two_options, DEFAULT_WEIGHTS, number_of_runs=200, top_n=1)
    times_first = int(result["times_in_top_n"].iloc[0])
    times_second = int(result["times_in_top_n"].iloc[1])
    assert times_first == 200 and times_second == 0, (times_first, times_second)
    print("PASS  B1 equal factor scores -> the more sought-after option wins every run (200 of 200)")


def get_air1_ranked():
    ranked, unrated, warnings, removed = rank_options(feasibility_air1, institutes, student_open,
                                                      demand_table=demand)
    return ranked


def test_no_change_means_base_top10_all_stable():
    ranked = get_air1_ranked()
    result = check_stability(ranked, DEFAULT_WEIGHTS, number_of_runs=50, max_change=0.0)
    base_top10 = result[result["option_id"] <= 10]
    assert (base_top10["share_in_top_n"] == 1.0).all(), base_top10
    assert (base_top10["stability_label"] == LABEL_STABLE).all()
    outside_top10 = result[result["option_id"] > 10]
    assert (outside_top10["times_in_top_n"] == 0).all()
    print("PASS  B2 max_change = 0 -> all base top-10 options are Stable pick (share 1.0)")


def test_same_seed_same_output():
    ranked = get_air1_ranked()
    started = time.time()
    first = check_stability(ranked, DEFAULT_WEIGHTS)
    seconds_taken = time.time() - started
    second = check_stability(ranked, DEFAULT_WEIGHTS)
    assert first.equals(second)
    different_seed = check_stability(ranked, DEFAULT_WEIGHTS, random_seed=7)
    print("PASS  B3 same seed twice -> identical output ("
          + str(len(ranked)) + " options x 500 runs in " + str(round(seconds_taken, 2)) + " s)")
    print("      (a different seed changes " + str(int((first["times_in_top_n"] != different_seed["times_in_top_n"]).sum()))
          + " counts slightly, as expected)")


if __name__ == "__main__":
    test_equal_scores_follow_tie_break()
    test_no_change_means_base_top10_all_stable()
    test_same_seed_same_output()
    test_all_rules_off_removes_nothing()
    test_fee_cap_below_every_fee_keeps_only_unknown_fee_rows()
    test_row_failing_two_rules_shows_both_reasons()
    test_rank_options_filters_before_scoring()
