"""
validate_chance.py — Out-of-sample check of the chance estimates.

Calibrate on target years 2024 and 2025 only, then predict 2026 (from 2023-2025
history) and compare the predicted chance with what actually happened.

Run:  python validate_chance.py
"""

import numpy as np
import pandas as pd

from loader import load_all_closing_ranks
from backtest import build_comparison
from feasibility import estimate_chance, label_from_chance, calibration_group_for


def calibration_from(comparison):
    is_pwd = comparison["seat_type"].str.contains("PwD", regex=False)
    groups = {
        "full_history": comparison[(comparison["years_of_data"] == 3) & (is_pwd == False)],
        "short_history": comparison[(comparison["years_of_data"] < 3) & (is_pwd == False)],
        "pwd": comparison[is_pwd],
    }
    calibration = {}
    for group_name in groups:
        ratios = []
        percentiles = []
        for percentile in range(0, 101):
            ratios.append(groups[group_name]["ratio_to_median"].quantile(percentile / 100))
            percentiles.append(percentile / 100)
        calibration[group_name] = (np.array(ratios), np.array(percentiles))
    return calibration


all_years = load_all_closing_ranks()
train = pd.concat([build_comparison(all_years, 2024), build_comparison(all_years, 2025)],
                  ignore_index=True)
test = build_comparison(all_years, 2026)
calibration = calibration_from(train)

records = []
grid_steps = 40
for _, seat in test.iterrows():
    group_name = calibration_group_for(seat["seat_type"], seat["years_of_data"], 3)
    lowest_rank_to_try = 0.5 * seat["lowest_cr"]
    highest_rank_to_try = 1.6 * seat["highest_cr"]
    step_size = (highest_rank_to_try - lowest_rank_to_try) / grid_steps
    for step_index in range(grid_steps + 1):
        student_rank = lowest_rank_to_try + step_index * step_size
        chance = estimate_chance(student_rank, seat["median_cr"], group_name, calibration)
        records.append({
            "group": group_name,
            "chance": chance,
            "label": label_from_chance(chance),
            "admitted": student_rank <= seat["target_cr"],
        })

results = pd.DataFrame(records)

print("Seats tested (2026):", len(test))
print()
print("=== By label: predicted vs actual admission rate ===")
summary_rows = []
for label_name in ["Safe", "Likely", "Reach", "Out"]:
    in_label = results[results["label"] == label_name]
    summary_rows.append({
        "label": label_name,
        "cases": len(in_label),
        "average predicted chance": round(in_label["chance"].mean(), 3),
        "actually admitted": round(in_label["admitted"].mean(), 3),
    })
print(pd.DataFrame(summary_rows).to_string(index=False))

print()
print("=== Calibration by predicted-chance band ===")
band_edges = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 1.0001]
band_rows = []
for band_index in range(len(band_edges) - 1):
    low_edge = band_edges[band_index]
    high_edge = band_edges[band_index + 1]
    in_band = results[(results["chance"] >= low_edge) & (results["chance"] < high_edge)]
    band_rows.append({
        "predicted band": str(int(low_edge * 100)) + "-" + str(min(100, int(high_edge * 100))) + "%",
        "cases": len(in_band),
        "average predicted": round(in_band["chance"].mean(), 3),
        "actually admitted": round(in_band["admitted"].mean(), 3),
    })
print(pd.DataFrame(band_rows).to_string(index=False))

print()
print("=== By calibration group ===")
for group_name in ["full_history", "short_history", "pwd"]:
    in_group = results[results["group"] == group_name]
    safe_cases = in_group[in_group["label"] == "Safe"]
    print(group_name, "| Safe actually admitted:", round(safe_cases["admitted"].mean(), 3),
          "| cases:", len(in_group))
