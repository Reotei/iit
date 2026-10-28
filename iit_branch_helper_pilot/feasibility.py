"""
feasibility.py — For one student, estimate the chance of getting each IIT program,
using past final-round closing ranks.

How the chance is estimated (see backtest.py):
  For thousands of past seats we know how much the next year's closing rank moved
  relative to the median of the three years before it. If a student's rank is r and
  a seat's median closing rank is M, the chance is the share of past cases where the
  next closing rank ended up at or above r, i.e. where CR(next) / M >= r / M.

  Seats with a short history and PwD seats move much more, so each has its own
  calibration group.

Labels are read straight off the chance:
  Safe   - 90% or more       Likely - 50% to 90%
  Reach  - 10% to 50%        Out    - below 10%

This module only answers "can I get it?". It never decides "how much do I want it?"
(scoring.py does that). JoSAA lets a student list choices in true preference order,
so chance should not push a preferred option down the list.
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
YEARS_TO_USE = [2024, 2025, 2026]
CALIBRATION_FILE = "data/chance_calibration.csv"

SAFE_CHANCE = 0.90
LIKELY_CHANCE = 0.50
REACH_CHANCE = 0.10

GENDER_NEUTRAL = "Gender-Neutral"
FEMALE_ONLY = "Female-only (including Supernumerary)"

# Higher number = better for the student. Used to pick the best label across pools.
LABEL_ORDER = {"Out": 0, "Reach": 1, "Likely": 2, "Safe": 3}


# ---------------------------------------------------------------------------
# Step 1: which seat pools can this student compete in, and with which rank?
# ---------------------------------------------------------------------------
def get_eligible_pools(category, is_female, is_pwd, crl_rank,
                       category_rank=None, pwd_rank=None):
    """
    category: "OPEN", "EWS", "OBC-NCL", "SC" or "ST"
    Returns a list of (seat_type, gender_pool, rank_to_compare).
    """
    gender_pools = [GENDER_NEUTRAL]
    if is_female:
        gender_pools.append(FEMALE_ONLY)

    pools = []
    for gender_pool in gender_pools:
        # Everyone competes for OPEN seats with their CRL rank
        if crl_rank is not None:
            pools.append(("OPEN", gender_pool, crl_rank))

        # Reserved-category students also compete for their own category's seats
        if category != "OPEN" and category_rank is not None:
            pools.append((category, gender_pool, category_rank))

        # PwD students also compete for PwD seats in their category
        if is_pwd and pwd_rank is not None:
            pwd_seat_type = category + " (PwD)"
            pools.append((pwd_seat_type, gender_pool, pwd_rank))

    return pools


# ---------------------------------------------------------------------------
# Step 2: chance from the calibration table
# ---------------------------------------------------------------------------
def load_calibration(file_path=CALIBRATION_FILE):
    """Returns {group_name: (ratios_sorted, percentiles)} for interpolation."""
    table = pd.read_csv(file_path)
    calibration = {}
    for group_name in table["group"].unique():
        group_rows = table[table["group"] == group_name].sort_values(by="percentile")
        ratios = group_rows["ratio_to_median"].to_numpy()
        percentiles = group_rows["percentile"].to_numpy() / 100.0
        calibration[group_name] = (ratios, percentiles)
    return calibration


def calibration_group_for(seat_type, years_of_data, total_years):
    if "(PwD)" in seat_type:
        return "pwd"
    if years_of_data < total_years:
        return "short_history"
    return "full_history"


def estimate_chance(student_rank, median_cr, group_name, calibration):
    """
    Share of past cases where next year's closing rank was >= the student's rank.
    ratio needed = student_rank / median_cr. The chance is 1 minus the share of
    past ratios below that.
    """
    ratios, percentiles = calibration[group_name]
    ratio_needed = student_rank / median_cr
    share_below = np.interp(ratio_needed, ratios, percentiles, left=0.0, right=1.0)
    chance = 1.0 - share_below
    return float(chance)


def label_from_chance(chance):
    if chance >= SAFE_CHANCE:
        return "Safe"
    if chance >= LIKELY_CHANCE:
        return "Likely"
    if chance >= REACH_CHANCE:
        return "Reach"
    return "Out"


# ---------------------------------------------------------------------------
# Step 3: closing-rank history per seat (institute + program + seat type + gender)
# ---------------------------------------------------------------------------
def build_seat_history(closing_rank_table, years_to_use=None):
    if years_to_use is None:
        years_to_use = YEARS_TO_USE
    in_window = closing_rank_table["year"].isin(years_to_use)
    not_preparatory = closing_rank_table["closing_is_preparatory"] == False
    usable_rows = closing_rank_table[in_window & not_preparatory]
    usable_rows = usable_rows.sort_values(by="year")  # so "last" below means the latest year

    seat_keys = ["institute", "program", "branch", "duration_years", "seat_type", "gender"]
    history = usable_rows.groupby(seat_keys).agg(
        lowest_cr=("closing_rank", "min"),
        median_cr=("closing_rank", "median"),
        highest_cr=("closing_rank", "max"),
        years_of_data=("year", "nunique"),
        latest_cr=("closing_rank", "last"),
        latest_year=("year", "last"),
    ).reset_index()
    return history


def closing_rank_by_year(closing_rank_table, institute, program, seat_type, gender):
    """All years' closing ranks for one seat, for charts. Includes 'P' flags."""
    is_seat = ((closing_rank_table["institute"] == institute)
               & (closing_rank_table["program"] == program)
               & (closing_rank_table["seat_type"] == seat_type)
               & (closing_rank_table["gender"] == gender))
    seat_rows = closing_rank_table[is_seat].sort_values(by="year")
    return seat_rows[["year", "closing_rank", "closing_is_preparatory"]]


# ---------------------------------------------------------------------------
# Step 4: label every program for one student, keeping the best pool
# ---------------------------------------------------------------------------
def feasibility_for_student(closing_rank_table, category, is_female, is_pwd,
                            crl_rank, category_rank=None, pwd_rank=None,
                            calibration=None):
    if calibration is None:
        calibration = load_calibration()

    history = build_seat_history(closing_rank_table)
    pools = get_eligible_pools(category, is_female, is_pwd, crl_rank,
                               category_rank, pwd_rank)
    total_years = len(YEARS_TO_USE)

    labelled_rows = []
    for seat_type, gender_pool, rank_to_compare in pools:
        is_this_pool = (history["seat_type"] == seat_type) & (history["gender"] == gender_pool)
        pool_history = history[is_this_pool]

        for _, seat in pool_history.iterrows():
            group_name = calibration_group_for(seat_type, seat["years_of_data"], total_years)
            chance = estimate_chance(rank_to_compare, seat["median_cr"], group_name, calibration)
            label = label_from_chance(chance)
            labelled_rows.append({
                "institute": seat["institute"],
                "program": seat["program"],
                "branch": seat["branch"],
                "duration_years": seat["duration_years"],
                "label": label,
                "label_score": LABEL_ORDER[label],
                "chance": chance,
                "seat_type": seat_type,
                "gender_pool": gender_pool,
                "via_pool": seat_type + " / " + gender_pool,
                "rank_used": rank_to_compare,
                "lowest_cr": seat["lowest_cr"],
                "median_cr": seat["median_cr"],
                "highest_cr": seat["highest_cr"],
                "latest_cr": seat["latest_cr"],
                "latest_year": seat["latest_year"],
                "years_of_data": seat["years_of_data"],
                "low_confidence": seat["years_of_data"] < total_years,
            })

    all_pools_table = pd.DataFrame(labelled_rows)
    if len(all_pools_table) == 0:
        return all_pools_table

    # Keep the best pool per program: highest chance first, then keep the first row
    sorted_table = all_pools_table.sort_values(
        by=["institute", "program", "chance"],
        ascending=[True, True, False],
    )
    best_per_program = sorted_table.drop_duplicates(subset=["institute", "program"], keep="first")
    return best_per_program.reset_index(drop=True)
