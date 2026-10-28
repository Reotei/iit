"""
scoring.py — turn a student's priorities into a preference score for every
program they can realistically get.

Answers "how much do I want it?". The chance of getting it comes from
feasibility.py and is shown next to the score, never mixed into it.

Factor status:
  interest           - student input (required)
  aptitude           - student's subject ratings x subject_relevance.csv (team assumption)
  salary_fit         - NIRF 2025 institute-wide median salary vs student's target
  institute_quality  - NIRF 2025 engineering score
  location           - institute region vs student's preferred regions
  finance            - IIT tuition after remission vs budget, and program length
  family             - family's ratings of branch groups
  career_path, flexibility, campus_life - no data yet (survey / institute rules)
"""

import numpy as np
import pandas as pd


# ===========================================================================
# PART A: branch groups
# Students rate 14 groups instead of ~150 JoSAA program names.
# Rules are checked in order; the FIRST keyword that appears wins.
# Order matters: "Mathematics and Computing" must hit Computing before
# a later rule could catch "Mathematics" as Science.
# ===========================================================================
BRANCH_GROUP_RULES = [
    # IIT BHU / ISM-style short names like "B. Tech. (ME) - M. Tech. in Mechatronics": check these first
    ("(CSE)", "Computing"),
    ("(ECE)", "Electrical and Electronics"),
    ("(EEE)", "Electrical and Electronics"),
    ("(ME)", "Mechanical and Production"),
    ("in CE.", "Civil and Infrastructure"),
    ("Integrated Circuit", "Electrical and Electronics"),  # must come before "Design"
    ("Mechanics and Computing", "Mechanical and Production"),  # IISc; judgement call
    ("Intelligent Systems", "Computing"),
    ("Quantum Science", "Pure and Applied Sciences"),  # judgement call: could be Electrical
    ("Unified Engineering", "General and Interdisciplinary"),
    ("Computer Science", "Computing"),
    ("Mathematics and Computing", "Computing"),
    ("Mathematics & Computing", "Computing"),
    ("Data Science", "Computing"),
    ("Artificial Intelligence", "Computing"),
    ("Electronics", "Electrical and Electronics"),
    ("Electrical", "Electrical and Electronics"),
    ("Instrumentation", "Electrical and Electronics"),
    ("Aerospace", "Aerospace"),
    ("Space Science", "Aerospace"),
    ("Mechatronics", "Mechanical and Production"),
    ("Industrial and Systems", "Mechanical and Production"),
    ("Computational Engineering", "Mechanical and Production"),  # judgement call: mechanics-heavy
    ("Mechanical", "Mechanical and Production"),
    ("Production", "Mechanical and Production"),
    ("Industrial Engineering", "Mechanical and Production"),
    ("Manufacturing", "Mechanical and Production"),
    ("Engineering and Computational Mechanics", "Mechanical and Production"),
    ("Naval Architecture", "Mechanical and Production"),
    ("Civil", "Civil and Infrastructure"),
    ("Environmental", "Civil and Infrastructure"),
    ("Biochemical", "Biotech and Bio-engineering"),
    ("Biotechnology", "Biotech and Bio-engineering"),
    ("Bioengineering", "Biotech and Bio-engineering"),
    ("Bio Engineering", "Biotech and Bio-engineering"),
    ("Pharmaceutical", "Biotech and Bio-engineering"),  # judgement call: could be Chemical
    ("Biological", "Biotech and Bio-engineering"),
    ("Biomedical", "Biotech and Bio-engineering"),
    ("Chemical", "Chemical and Process"),
    ("Industrial Chemistry", "Chemical and Process"),
    ("Metallurg", "Materials and Metallurgy"),
    ("Materials", "Materials and Metallurgy"),
    ("Ceramic", "Materials and Metallurgy"),
    ("Mining", "Earth, Mining and Energy"),
    ("Petroleum", "Earth, Mining and Energy"),
    ("Geolog", "Earth, Mining and Energy"),
    ("Geophysic", "Earth, Mining and Energy"),
    ("Earth Science", "Earth, Mining and Energy"),
    ("Ocean", "Earth, Mining and Energy"),
    ("Energy", "Earth, Mining and Energy"),
    ("Textile", "Textile"),
    ("Architecture", "Architecture and Design"),
    ("Design", "Architecture and Design"),
    ("Engineering Physics", "Pure and Applied Sciences"),
    ("Physics", "Pure and Applied Sciences"),
    ("Chemistry", "Pure and Applied Sciences"),
    ("Mathematics", "Pure and Applied Sciences"),
    ("Physical Science", "Pure and Applied Sciences"),
    ("Economics", "Pure and Applied Sciences"),
    ("Agricultur", "Agriculture and Food"),
    ("General Engineering", "General and Interdisciplinary"),
    ("Engineering Science", "General and Interdisciplinary"),
    ("Interdisciplinary", "General and Interdisciplinary"),
]

ALL_BRANCH_GROUPS = [
    "Computing", "Electrical and Electronics", "Aerospace", "Mechanical and Production",
    "Civil and Infrastructure", "Biotech and Bio-engineering", "Chemical and Process",
    "Materials and Metallurgy", "Earth, Mining and Energy", "Textile",
    "Architecture and Design", "Pure and Applied Sciences", "Agriculture and Food",
    "General and Interdisciplinary",
]

ABU_DHABI_PREFIX = "Abu Dhabi Campus - "


def clean_branch_name(branch_name):
    """Remove the Abu Dhabi campus prefix so the branch maps to its normal group."""
    if branch_name.startswith(ABU_DHABI_PREFIX):
        return branch_name[len(ABU_DHABI_PREFIX):]
    return branch_name


def get_branch_group(branch_name):
    cleaned_name = clean_branch_name(branch_name)
    for keyword, group_name in BRANCH_GROUP_RULES:
        if keyword.lower() in cleaned_name.lower():
            return group_name
    return "Other"


# ===========================================================================
# PART B: weights
# ===========================================================================
FACTOR_NAMES = [
    "interest", "aptitude", "career_path", "salary_fit", "institute_quality",
    "demand", "flexibility", "location", "finance", "family", "campus_life",
]

# PLACEHOLDER importance points. Replace with survey Q31 results.
# The app offers these steps: Ignore 0, A little 5, Some 10, A lot 20, Most of all 30.
DEFAULT_IMPORTANCE = {
    "interest": 20,
    "aptitude": 10,
    "career_path": 10,
    "salary_fit": 10,
    "institute_quality": 10,
    "demand": 5,          # deliberately low: copying past toppers is the habit we want to question
    "flexibility": 5,
    "location": 10,
    "finance": 10,
    "family": 10,
    "campus_life": 5,
}


def weights_from_importance(importance_points):
    """Turn importance points into weights that sum to 1."""
    total_points = sum(importance_points.values())
    weights = {}
    for factor_name in importance_points:
        if total_points > 0:
            weights[factor_name] = importance_points[factor_name] / total_points
        else:
            weights[factor_name] = 0.0
    return weights


DEFAULT_WEIGHTS = weights_from_importance(DEFAULT_IMPORTANCE)


def weights_from_ranking(ranked_factor_names):
    """
    Rank-order centroid: turn a ranking (most important first) into weights.
    For n factors, the factor at position k (1-based) gets
        weight_k = (1/n) * (1/k + 1/(k+1) + ... + 1/n)
    Weights always sum to 1, and higher-ranked factors always get more.
    """
    number_of_factors = len(ranked_factor_names)
    weights = {}
    for position_index in range(number_of_factors):
        position = position_index + 1
        running_total = 0.0
        for later_position in range(position, number_of_factors + 1):
            running_total = running_total + 1.0 / later_position
        weights[ranked_factor_names[position_index]] = running_total / number_of_factors
    return weights


# ===========================================================================
# PART C: institute and reference data
# ===========================================================================
INSTITUTES_FILE = "data/institutes.csv"
NIRF_FILE = "data/nirf_2025.csv"
SUBJECT_RELEVANCE_FILE = "data/subject_relevance.csv"

SUBJECTS = ["physics", "chemistry", "mathematics", "biology", "computing", "drawing_design"]

TUITION_PER_YEAR = 200000  # Rs 1,00,000 per semester (see data/fees.csv)
INCOME_BANDS = ["Below Rs 1 lakh", "Rs 1-5 lakh", "Above Rs 5 lakh", "Prefer not to say"]


def load_institute_table():
    """One row per institute: location plus NIRF 2025 summary."""
    institutes = pd.read_csv(INSTITUTES_FILE)
    nirf = pd.read_csv(NIRF_FILE)

    summary_rows = []
    for institute_name in nirf["institute"].unique():
        rows = nirf[nirf["institute"] == institute_name].sort_values(by="graduating_year")
        latest = rows.iloc[-1]
        summary_rows.append({
            "institute": institute_name,
            "nirf_rank": int(latest["nirf_engineering_rank_2025"]),
            "nirf_score": float(latest["nirf_engineering_score_2025"]),
            "median_salary_inr": float(rows["ug4_median_salary_inr"].mean()),  # average of 3 batches
            "placed_share": float(latest["ug4_placed"] / latest["ug4_graduates"]),
            "higher_studies_share": float(latest["ug4_higher_studies"] / latest["ug4_graduates"]),
        })
    nirf_summary = pd.DataFrame(summary_rows)

    # Institute quality: rescale NIRF score to 0-1 across the IITs we have.
    lowest_score = nirf_summary["nirf_score"].min()
    highest_score = nirf_summary["nirf_score"].max()
    quality_values = []
    for score_value in nirf_summary["nirf_score"]:
        quality_values.append((score_value - lowest_score) / (highest_score - lowest_score))
    nirf_summary["nirf_quality"] = quality_values

    table = institutes.merge(nirf_summary, on="institute", how="left")
    return table


DEMAND_YEARS = [2024, 2025, 2026]


def build_demand_table(closing_rank_table):
    """
    How sought-after each program is, from what students actually chose.

    Uses OPEN, gender-neutral seats only, so every program is measured on the same
    pool. A program whose seats fill up at a better (smaller) closing rank was
    preferred by more top-ranked students.

    The score uses the logarithm of the median closing rank, rescaled so the most
    sought-after IIT program scores 1 and the least sought-after scores 0. A log
    scale fits ranks: the gap between rank 67 and 159 means far more than the gap
    between 10,067 and 10,159.
    """
    is_open = closing_rank_table["seat_type"] == "OPEN"
    is_neutral = closing_rank_table["gender"] == "Gender-Neutral"
    in_years = closing_rank_table["year"].isin(DEMAND_YEARS)
    is_normal = closing_rank_table["closing_is_preparatory"] == False
    rows = closing_rank_table[is_open & is_neutral & in_years & is_normal]

    demand = rows.groupby(["institute", "program"]).agg(
        demand_median_cr=("closing_rank", "median"),
    ).reset_index()

    log_ranks = np.log(demand["demand_median_cr"].astype(float))
    best_log_rank = log_ranks.min()
    worst_log_rank = log_ranks.max()
    demand_scores = []
    for log_rank in log_ranks:
        demand_scores.append(1.0 - (log_rank - best_log_rank) / (worst_log_rank - best_log_rank))
    demand["demand_score"] = demand_scores
    return demand


def load_subject_relevance():
    table = pd.read_csv(SUBJECT_RELEVANCE_FILE)
    relevance = {}
    for _, row in table.iterrows():
        subject_weights = {}
        for subject_name in SUBJECTS:
            subject_weights[subject_name] = float(row[subject_name])
        relevance[row["branch_group"]] = subject_weights
    return relevance


SUBJECT_RELEVANCE = load_subject_relevance()


def net_tuition_per_year(category, is_pwd, income_band):
    """IIT tuition after remission (data/fees.csv). Hostel and mess not included."""
    if category == "SC" or category == "ST" or is_pwd:
        return 0
    if income_band == "Below Rs 1 lakh":
        return 0
    if income_band == "Rs 1-5 lakh":
        return round(TUITION_PER_YEAR / 3)
    return TUITION_PER_YEAR


# ===========================================================================
# PART D: factor score functions
# Each returns (score, note). score is 0-1, or None when the factor is not used.
# None is NOT the same as 0: an unused factor is left out, not punished.
# When data is missing for ONE option only, the score is a neutral 0.5 with a
# note, so that option neither gains nor loses from the gap.
# ===========================================================================
NEUTRAL_SCORE = 0.5


def rating_to_score(rating):
    """A 1-5 rating becomes 0, 0.25, 0.5, 0.75 or 1."""
    return (rating - 1) / 4


def is_missing(value):
    if value is None:
        return True
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False


def score_interest(option, student):
    ratings = student.get("interest_ratings", {})
    group_name = option["branch_group"]
    if group_name not in ratings:
        return (None, "")
    return (rating_to_score(ratings[group_name]), "")


def score_aptitude(option, student):
    subject_ratings = student.get("subject_ratings", {})
    if len(subject_ratings) == 0:
        return (None, "")
    group_name = option["branch_group"]
    if group_name not in SUBJECT_RELEVANCE:
        return (NEUTRAL_SCORE, "No subject profile for this branch group.")
    relevance = SUBJECT_RELEVANCE[group_name]
    weighted_total = 0.0
    relevance_total = 0.0
    for subject_name in SUBJECTS:
        if subject_name in subject_ratings:
            weighted_total = weighted_total + relevance[subject_name] * rating_to_score(subject_ratings[subject_name])
            relevance_total = relevance_total + relevance[subject_name]
    if relevance_total == 0:
        return (NEUTRAL_SCORE, "")
    return (weighted_total / relevance_total, "")


def score_salary_fit(option, student):
    desired_lpa = student.get("desired_salary_lpa", None)
    if desired_lpa is None or desired_lpa <= 0:
        return (None, "")
    median_salary = option["median_salary_inr"]
    if is_missing(median_salary):
        if option["is_abu_dhabi"]:
            return (NEUTRAL_SCORE, "Abu Dhabi campus: no salary data of its own yet, so salary is scored neutral.")
        return (NEUTRAL_SCORE, "No NIRF salary data for this institute, so salary is scored neutral.")
    median_lpa = median_salary / 100000
    if median_lpa >= desired_lpa:
        return (1.0, "")
    return (median_lpa / desired_lpa, "")


def score_institute_quality(option, student):
    quality = option["nirf_quality"]
    if is_missing(quality):
        if option["is_abu_dhabi"]:
            return (NEUTRAL_SCORE, "Abu Dhabi campus: not ranked separately by NIRF, so it does not borrow "
                                   "IIT Delhi's ranking. Scored neutral.")
        return (NEUTRAL_SCORE, "Not in the NIRF 2025 engineering ranking, so ranking is scored neutral.")
    return (float(quality), "")


def score_demand(option, student):
    demand_value = option.get("demand_score", None)
    if is_missing(demand_value):
        return (NEUTRAL_SCORE, "No OPEN closing-rank data to measure how sought-after this program is.")
    return (float(demand_value), "")


def score_location(option, student):
    preferred_regions = student.get("preferred_regions", [])
    if len(preferred_regions) == 0:
        return (None, "")  # student has no location preference: don't score it
    if option["region"] in preferred_regions:
        return (1.0, "")
    return (0.0, "")


def score_finance(option, student):
    """
    Two parts, averaged when both are given:
      affordability - tuition after remission vs the yearly amount the family can pay
      length        - a student who needs to earn early is better served by 4 years
    """
    parts = []
    note = ""

    yearly_budget = student.get("tuition_budget_per_year", None)
    if yearly_budget is not None:
        if option["is_abu_dhabi"]:
            parts.append(NEUTRAL_SCORE)
            note = "Abu Dhabi campus fees differ and are not in our data."
        else:
            yearly_cost = net_tuition_per_year(student.get("category", "OPEN"),
                                               student.get("is_pwd", False),
                                               student.get("income_band", None))
            if yearly_cost <= yearly_budget:
                parts.append(1.0)
            else:
                parts.append(yearly_budget / yearly_cost)

    needs_early_earning = student.get("needs_early_earning", None)
    if needs_early_earning is not None:
        if needs_early_earning == False or option["duration_years"] <= 4:
            parts.append(1.0)
        else:
            parts.append(0.4)  # placeholder penalty for a 5-year program; to calibrate

    if len(parts) == 0:
        return (None, "")
    return (sum(parts) / len(parts), note)


def score_family(option, student):
    """
    If the family gave no ratings at all, the factor is not used.
    If they rated some groups, an unrated group means "no stated view" = neutral.
    """
    ratings = student.get("family_ratings", {})
    if len(ratings) == 0:
        return (None, "")
    group_name = option["branch_group"]
    if group_name not in ratings:
        return (NEUTRAL_SCORE, "")
    return (rating_to_score(ratings[group_name]), "")


def score_not_available_yet(option, student):
    return (None, "")


FACTOR_FUNCTIONS = {
    "interest": score_interest,
    "aptitude": score_aptitude,
    "career_path": score_not_available_yet,       # needs branch-level outcome data
    "salary_fit": score_salary_fit,
    "institute_quality": score_institute_quality,
    "demand": score_demand,
    "flexibility": score_not_available_yet,       # needs minors / branch-change rules
    "location": score_location,
    "finance": score_finance,
    "family": score_family,
    "campus_life": score_not_available_yet,       # needs survey Section F
}

FACTORS_WITHOUT_DATA = ["career_path", "flexibility", "campus_life"]


# ===========================================================================
# PART E: the weighted sum for one option
# ===========================================================================
def score_one_option(option, student, weights):
    factor_scores = {}
    notes = []
    weighted_total = 0.0
    weight_with_data = 0.0
    missing_factors = []

    for factor_name in FACTOR_NAMES:
        factor_function = FACTOR_FUNCTIONS[factor_name]
        factor_score, note = factor_function(option, student)
        factor_scores[factor_name] = factor_score
        if note != "":
            notes.append(note)

        factor_weight = weights.get(factor_name, 0.0)
        if factor_score is None:
            missing_factors.append(factor_name)
        else:
            weighted_total = weighted_total + factor_weight * factor_score
            weight_with_data = weight_with_data + factor_weight

    total_weight = sum(weights.values())

    if weight_with_data == 0:
        preference_score = None
        coverage = 0.0
    else:
        preference_score = 100 * weighted_total / weight_with_data
        coverage = weight_with_data / total_weight

    # Contribution of each factor to the final score (points out of 100)
    contributions = {}
    for factor_name in FACTOR_NAMES:
        factor_score = factor_scores[factor_name]
        if factor_score is not None and weight_with_data > 0:
            contributions[factor_name] = 100 * weights[factor_name] * factor_score / weight_with_data

    return {
        "preference_score": preference_score,
        "coverage": coverage,
        "factor_scores": factor_scores,
        "contributions": contributions,
        "missing_factors": missing_factors,
        "notes": notes,
    }


# ===========================================================================
# PART F: rank all feasible options for a student
# ===========================================================================
MINIMUM_SAFE_OPTIONS = 5


NIRF_COLUMNS = ["nirf_rank", "nirf_score", "nirf_quality", "median_salary_inr",
                "placed_share", "higher_studies_share"]


def prepare_options(feasibility_table, institute_table, demand_table=None):
    """Add branch group, location, NIRF and demand data to each feasible option."""
    is_not_out = feasibility_table["label"] != "Out"
    options = feasibility_table[is_not_out].copy()

    options["branch_group"] = options["branch"].apply(get_branch_group)
    options = options.merge(institute_table, on="institute", how="left")

    if demand_table is not None:
        options = options.merge(demand_table, on=["institute", "program"], how="left")
    else:
        options["demand_score"] = None
        options["demand_median_cr"] = None

    # The Abu Dhabi campus is not part of IIT Delhi's NIRF data: its graduates,
    # salaries and ranking are not known yet, so it must not borrow Delhi's.
    is_abu_dhabi = options["branch"].str.startswith(ABU_DHABI_PREFIX)
    options["is_abu_dhabi"] = is_abu_dhabi
    options.loc[is_abu_dhabi, "region"] = "Abroad (Abu Dhabi)"
    options.loc[is_abu_dhabi, "state"] = "Abu Dhabi"
    options.loc[is_abu_dhabi, "city"] = "Abu Dhabi"
    for column_name in NIRF_COLUMNS:
        options.loc[is_abu_dhabi, column_name] = float("nan")
    return options


def rank_options(feasibility_table, institute_table, student, weights=None, demand_table=None,
                 must_haves=None):
    """
    Pipeline: eligible options -> must-have filter -> score -> sort.
    Returns (ranked, unrated_options, warnings, removed_options).
    """
    # Imported here, not at the top, because musthaves.py imports from this file.
    from musthaves import apply_must_haves

    if weights is None:
        weights = DEFAULT_WEIGHTS

    options = prepare_options(feasibility_table, institute_table, demand_table)

    # Step A: the student's own dealbreakers (all off unless the student turns them on)
    options, removed_options = apply_must_haves(options, must_haves, student)

    # Interest is REQUIRED. Options in a group the student has not rated are set
    # aside (not scored), otherwise they would be scored without the most
    # important factor and could unfairly jump to the top.
    rated_groups = list(student.get("interest_ratings", {}).keys())
    group_is_rated = options["branch_group"].isin(rated_groups)
    unrated_options = options[group_is_rated == False].copy()
    options = options[group_is_rated].copy()

    results = []
    for _, option in options.iterrows():
        result = score_one_option(option, student, weights)
        results.append(result)

    options["preference_score"] = [r["preference_score"] for r in results]
    options["coverage"] = [r["coverage"] for r in results]
    options["factor_scores"] = [r["factor_scores"] for r in results]
    options["contributions"] = [r["contributions"] for r in results]
    options["missing_factors"] = [r["missing_factors"] for r in results]
    options["notes"] = [r["notes"] for r in results]

    # Sort by preference. Exact ties are broken by how sought-after the program is
    # (a real signal), never by chance and never by alphabetical order.
    options["tie_break_demand"] = options["demand_score"].fillna(NEUTRAL_SCORE)
    options["rounded_for_sort"] = options["preference_score"].round(6)
    ranked = options.sort_values(by=["rounded_for_sort", "tie_break_demand"],
                                 ascending=[False, False]).reset_index(drop=True)
    ranked.insert(0, "preference_rank", range(1, len(ranked) + 1))

    warnings = []
    safe_count = (ranked["label"] == "Safe").sum()
    if safe_count < MINIMUM_SAFE_OPTIONS:
        warnings.append("Only " + str(safe_count) + " Safe options. Add more Safe options "
                        "near the end of your JoSAA choice list.")
    if len(unrated_options) > 0:
        unrated_group_names = sorted(unrated_options["branch_group"].unique())
        warnings.append(str(len(unrated_options)) + " options not scored because you did not rate: "
                        + ", ".join(unrated_group_names))

    return ranked, unrated_options, warnings, removed_options


def get_points_from_pair(factor_and_points):
    """Used for sorting: from ("interest", 12.5) return 12.5."""
    points = factor_and_points[1]
    return points


def explain_option(ranked_row):
    """Plain-language explanation for one option."""
    contributions = ranked_row["contributions"]
    sorted_factors = sorted(contributions.items(), key=get_points_from_pair, reverse=True)

    lines = []
    lines.append(ranked_row["branch"] + " at " + ranked_row["institute"]
                 + " - score " + str(round(ranked_row["preference_score"], 1))
                 + " / 100, " + ranked_row["label"]
                 + " (about " + str(round(100 * ranked_row["chance"])) + "% chance, via "
                 + ranked_row["via_pool"] + ")")
    for factor_name, points in sorted_factors:
        lines.append("  " + factor_name + ": " + str(round(points, 1)) + " points")
    lines.append("  Scored on " + str(round(100 * ranked_row["coverage"])) + "% of your weights; missing: "
                 + ", ".join(ranked_row["missing_factors"]))
    for note in ranked_row["notes"]:
        lines.append("  Note: " + note)
    if ranked_row["low_confidence"]:
        lines.append("  Note: fewer than 3 years of closing-rank data for this seat.")
    return "\n".join(lines)
