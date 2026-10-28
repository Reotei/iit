"""
musthaves.py — Step A: the student's own dealbreakers.

Runs AFTER feasibility (only options the student can realistically get) and
BEFORE scoring, so scores and the stability check only see options the student
would accept.

Fairness rules:
  - Every rule is OFF unless the student switches it on. The tool never removes
    options on the student's behalf.
  - Nothing is dropped silently: every removed option keeps a plain-language
    reason, and the app lists them under "Removed by your must-haves".
  - If a rule cannot be checked because data is missing (fees of the Abu Dhabi
    campus), the option is KEPT and flagged, not removed.

must_haves is a dict. A rule is off when its value is None / False / empty:
  "max_tuition_per_year": number in Rs, or None
  "allowed_regions":      list of region names, or []
  "exclude_five_year":    True / False
  "excluded_groups":      list of branch-group names, or []

The tuition check needs the student's category, PwD status and income band,
because IIT tuition after remission depends on the student, not the institute.
"""

from scoring import net_tuition_per_year
import ui


FEES_UNKNOWN_FLAG = "Fees unknown - check before listing"


def rule_is_on(must_haves, rule_name):
    value = must_haves.get(rule_name, None)
    if value is None:
        return False
    if value is False:
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True


def check_one_option(option, must_haves, yearly_tuition):
    """Returns (list of reasons it fails, list of flags). Empty reasons = keep."""
    reasons = []
    flags = []

    # Rule 1: maximum yearly tuition after remission
    if rule_is_on(must_haves, "max_tuition_per_year"):
        tuition_limit = must_haves["max_tuition_per_year"]
        if option["is_abu_dhabi"]:
            flags.append(FEES_UNKNOWN_FLAG)
        elif yearly_tuition > tuition_limit:
            reasons.append("Tuition after remission " + ui.format_rupees(yearly_tuition)
                           + "/yr is above your limit of " + ui.format_rupees(tuition_limit) + "/yr")

    # Rule 2: allowed regions only
    if rule_is_on(must_haves, "allowed_regions"):
        allowed_regions = must_haves["allowed_regions"]
        if option["region"] not in allowed_regions:
            reasons.append("In the " + str(option["region"]) + " region, which is not in your allowed regions")

    # Rule 3: no 5-year programmes
    if rule_is_on(must_haves, "exclude_five_year"):
        if option["duration_years"] >= 5:
            reasons.append("A " + str(int(option["duration_years"])) + "-year program, and you chose 4-year programs only")

    # Rule 4: branch groups the student never wants to see
    if rule_is_on(must_haves, "excluded_groups"):
        excluded_groups = must_haves["excluded_groups"]
        if option["branch_group"] in excluded_groups:
            reasons.append(option["branch_group"] + " is a branch group you chose to leave out")

    return reasons, flags


def apply_must_haves(options_table, must_haves, student=None):
    """
    options_table: options after prepare_options (has region, branch_group,
                   duration_years, is_abu_dhabi).
    Returns (kept_options, removed_options).
      kept_options gets a "must_have_flags" column (list of strings).
      removed_options gets a "removed_reason" column (all reasons, joined by "; ").
    """
    if must_haves is None:
        must_haves = {}
    if student is None:
        student = {}

    yearly_tuition = net_tuition_per_year(student.get("category", "OPEN"),
                                          student.get("is_pwd", False),
                                          student.get("income_band", None))

    keep_flags = []
    reasons_column = []
    flags_column = []
    for _, option in options_table.iterrows():
        reasons, flags = check_one_option(option, must_haves, yearly_tuition)
        keep_flags.append(len(reasons) == 0)
        reasons_column.append("; ".join(reasons))
        flags_column.append(flags)

    table = options_table.copy()
    table["removed_reason"] = reasons_column
    table["must_have_flags"] = flags_column
    table["passes_must_haves"] = keep_flags

    is_kept = table["passes_must_haves"] == True
    kept_options = table[is_kept].drop(columns=["removed_reason", "passes_must_haves"]).copy()
    removed_options = table[is_kept == False].drop(columns=["passes_must_haves"]).copy()
    return kept_options, removed_options
