"""
backtest.py — How well do past closing ranks predict next year's?

For each target year T, take every seat (institute + program + seat type + gender)
that has a normal (non-preparatory) closing rank in T and in at least one of the
three years before T. Then compare T's closing rank with the history:

    ratio_to_lowest  = CR(T) / lowest CR in history
    ratio_to_median  = CR(T) / median CR in history
    ratio_to_highest = CR(T) / highest CR in history

A student with rank r gets the seat in year T if r <= CR(T).
So "Safe if r <= f x lowest" is right 95% of the time when f is the 5th percentile
of ratio_to_lowest, and "Reach if r <= g x highest" still has a ~10% chance when
g is the 90th percentile of ratio_to_highest.

Run:  python backtest.py
"""

import pandas as pd
from loader import load_closing_ranks

FILES = [
    "data/josaa_iit_final_round_2021_2025.csv",
    "data/josaa_iit_final_round_2026.csv",
]
TARGET_YEARS = [2024, 2025, 2026]
SEAT_KEYS = ["institute", "program", "seat_type", "gender"]


def load_all_years():
    tables = []
    for file_path in FILES:
        tables.append(load_closing_ranks(file_path))
    return pd.concat(tables, ignore_index=True)


def build_comparison(all_years, target_year):
    history_years = [target_year - 3, target_year - 2, target_year - 1]

    normal_rows = all_years[all_years["closing_is_preparatory"] == False]

    in_history = normal_rows["year"].isin(history_years)
    history = normal_rows[in_history].groupby(SEAT_KEYS).agg(
        lowest_cr=("closing_rank", "min"),
        median_cr=("closing_rank", "median"),
        highest_cr=("closing_rank", "max"),
        years_of_data=("year", "nunique"),
    ).reset_index()

    is_target = normal_rows["year"] == target_year
    target = normal_rows[is_target][SEAT_KEYS + ["closing_rank"]].rename(
        columns={"closing_rank": "target_cr"})

    joined = history.merge(target, on=SEAT_KEYS, how="inner")
    joined["target_year"] = target_year
    joined["ratio_to_lowest"] = joined["target_cr"] / joined["lowest_cr"]
    joined["ratio_to_median"] = joined["target_cr"] / joined["median_cr"]
    joined["ratio_to_highest"] = joined["target_cr"] / joined["highest_cr"]
    return joined


def seat_group(row):
    if row["seat_type"] == "OPEN" and row["gender"] == "Gender-Neutral":
        return "OPEN, gender-neutral"
    if "(PwD)" in row["seat_type"]:
        return "PwD seats"
    if row["gender"] != "Gender-Neutral":
        return "Female-only seats"
    return "Category seats, gender-neutral"


def summarise(comparison, label):
    lowest_q05 = comparison["ratio_to_lowest"].quantile(0.05)
    share_above_median = (comparison["ratio_to_median"] >= 1).mean()
    highest_q90 = comparison["ratio_to_highest"].quantile(0.90)
    return {
        "group": label,
        "seats": len(comparison),
        "safe_factor (5th pct of CR/lowest)": round(lowest_q05, 3),
        "P(admit | rank = median)": round(share_above_median, 3),
        "reach_factor (90th pct of CR/highest)": round(highest_q90, 3),
    }


def evaluate_rule(comparison, safe_factor, reach_factor):
    """Admission rate inside each label band, using a grid of student ranks per seat."""
    results = {"Safe": [0, 0], "Likely": [0, 0], "Reach": [0, 0], "Out": [0, 0]}
    grid_steps = 60
    for _, seat in comparison.iterrows():
        lowest_rank_to_try = 0.3 * seat["lowest_cr"]
        highest_rank_to_try = 2.0 * seat["highest_cr"]
        step_size = (highest_rank_to_try - lowest_rank_to_try) / grid_steps
        for step_index in range(grid_steps + 1):
            student_rank = lowest_rank_to_try + step_index * step_size
            if student_rank <= safe_factor * seat["lowest_cr"]:
                label = "Safe"
            elif student_rank <= seat["median_cr"]:
                label = "Likely"
            elif student_rank <= reach_factor * seat["highest_cr"]:
                label = "Reach"
            else:
                label = "Out"
            admitted = student_rank <= seat["target_cr"]
            results[label][1] = results[label][1] + 1
            if admitted:
                results[label][0] = results[label][0] + 1
    rates = {}
    for label_name in results:
        admitted_count, total_count = results[label_name]
        if total_count > 0:
            rates[label_name] = round(admitted_count / total_count, 3)
        else:
            rates[label_name] = None
    return rates


if __name__ == "__main__":
    all_years = load_all_years()

    comparisons = []
    for target_year in TARGET_YEARS:
        comparisons.append(build_comparison(all_years, target_year))
    combined = pd.concat(comparisons, ignore_index=True)
    combined["seat_group"] = combined.apply(seat_group, axis=1)

    full_history = combined[combined["years_of_data"] == 3]

    print("=== Year-to-year movement, seats with 3 years of history ===")
    rows = []
    for target_year in TARGET_YEARS:
        rows.append(summarise(full_history[full_history["target_year"] == target_year],
                              "target " + str(target_year)))
    rows.append(summarise(full_history, "all three years"))
    for group_name in sorted(full_history["seat_group"].unique()):
        rows.append(summarise(full_history[full_history["seat_group"] == group_name], group_name))
    rows.append(summarise(combined[combined["years_of_data"] < 3], "seats with only 1-2 years"))
    print(pd.DataFrame(rows).to_string(index=False))

    # Save the distribution of CR(T) / median CR(history) for each confidence group.
    # feasibility.py uses it to estimate a chance: the share of past cases where the
    # next year's closing rank ended up at or above the student's rank.
    is_pwd = combined["seat_type"].str.contains("PwD", regex=False)
    group_tables = {
        "full_history": combined[(combined["years_of_data"] == 3) & (is_pwd == False)],
        "short_history": combined[(combined["years_of_data"] < 3) & (is_pwd == False)],
        "pwd": combined[is_pwd],
    }
    calibration_rows = []
    for group_name in group_tables:
        group_table = group_tables[group_name]
        for percentile in range(0, 101):
            calibration_rows.append({
                "group": group_name,
                "percentile": percentile,
                "ratio_to_median": round(group_table["ratio_to_median"].quantile(percentile / 100), 5),
                "ratio_to_lowest": round(group_table["ratio_to_lowest"].quantile(percentile / 100), 5),
                "ratio_to_highest": round(group_table["ratio_to_highest"].quantile(percentile / 100), 5),
                "seats": len(group_table),
            })
    pd.DataFrame(calibration_rows).to_csv("data/chance_calibration.csv", index=False)
    print()
    print("Saved data/chance_calibration.csv")
    for group_name in group_tables:
        group_table = group_tables[group_name]
        print("  ", group_name, ": seats", len(group_table),
              "| safe factor (5th pct)", round(group_table["ratio_to_lowest"].quantile(0.05), 3),
              "| reach factor (90th pct)", round(group_table["ratio_to_highest"].quantile(0.90), 3))

    print()
    print("=== Admission rate inside each label (all three target years) ===")
    for safe_factor, reach_factor in [(0.9, 1.1), (0.8, 1.1), (0.75, 1.15), (0.7, 1.2)]:
        rates = evaluate_rule(full_history, safe_factor, reach_factor)
        print("safe", safe_factor, "reach", reach_factor, "->", rates)
