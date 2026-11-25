"""
drift.py — drift early-warning check (PROPOSED DESIGN, not validated).

The problem (research brief, drivers D4 and D5, hypothesis H2): many core-branch
students drift away from their field by the end of year 2, often without ever
deciding to.

The idea: a short self-check, filled in by the student, that spots signs of drift
while there is still time, and suggests concrete help (a mentor, a project, a team).

Scoring uses the same method as the branch tool:
  1. Each answer becomes a risk between 0 (no sign of drift) and 1 (strong sign).
  2. Risk score = sum of (weight x risk) / sum of weights, x 100.
  3. Level: Low below 35, Medium 35 to 60, High 60 or more.

Fairness rules:
  - A student who has decided on a non-core career and is happy with it gets NO alert.
    That is an informed choice, which is what our project wants to protect.
  - Only the student's own answers are used: no grades pulled from college systems, and
    no category, gender, income or home state.
  - The result is for the student only and is used to offer help, never for grades
    or rankings. Nothing is saved.

The weights and the risk values for each answer are TEAM ASSUMPTIONS, to be replaced
using our survey (hypotheses H2, H4, H6) and a pilot.
"""

CAREER_PLAN_OPTIONS = [
    "I want a career in my own field",
    "Not sure yet",
    "Leaning towards a non-core job",
    "Decided on a non-core career, and happy with it",
]
INFORMED_NON_CORE_CHOICE = "Decided on a non-core career, and happy with it"

GRADE_TREND_OPTIONS = ["Improving", "Steady", "Falling"]
YES_NO_OPTIONS = ["Yes", "No"]

SIGNAL_NAMES = ["career_plan", "core_course_interest", "grade_trend", "core_project",
                "technical_team", "knows_core_alumni"]

SIGNAL_LABELS = {
    "career_plan": "Your career plan",
    "core_course_interest": "Interest in your core courses",
    "grade_trend": "Core-course grades",
    "core_project": "Core project or internship",
    "technical_team": "Technical team or club",
    "knows_core_alumni": "Know someone working in core",
}

# Team assumption: how much each sign counts (points, turned into shares below)
DEFAULT_DRIFT_WEIGHTS = {
    "career_plan": 30,
    "core_course_interest": 20,
    "grade_trend": 15,
    "core_project": 15,
    "technical_team": 10,
    "knows_core_alumni": 10,
}

# Team assumption: risk for each answer
CAREER_PLAN_RISK = {
    "I want a career in my own field": 0.0,
    "Not sure yet": 0.5,
    "Leaning towards a non-core job": 1.0,
}
GRADE_TREND_RISK = {"Improving": 0.0, "Steady": 0.25, "Falling": 1.0}
YES_NO_RISK = {"Yes": 0.0, "No": 1.0}

LOW_LIMIT = 35
HIGH_LIMIT = 60

# Help offered when a sign is strong (risk 0.5 or more)
SUPPORT_FOR_SIGNAL = {
    "career_plan": "A short career conversation with a senior or alumnus working in your field.",
    "core_course_interest": "See a real problem from your field: a lab visit, plant visit or industry talk.",
    "grade_trend": "Peer tutoring or TA office hours for the core courses that are slipping.",
    "core_project": "Apply for a core project: an industry studio course or the internship matching round.",
    "technical_team": "Try a technical team (Formula, UAV, solar car, robotics) for one semester.",
    "knows_core_alumni": "Get matched with an alumni mentor who works in your field.",
}
STRONG_SIGN = 0.5


def interest_risk(interest_level):
    """Interest from 1 (none) to 5 (a lot) -> risk from 1.0 down to 0.0."""
    return (5 - interest_level) / 4


def signal_risks(answers):
    """Turn the student's answers into a risk between 0 and 1 for each sign."""
    risks = {}
    risks["career_plan"] = CAREER_PLAN_RISK[answers["career_plan"]]
    risks["core_course_interest"] = interest_risk(answers["core_course_interest"])
    risks["grade_trend"] = GRADE_TREND_RISK[answers["grade_trend"]]
    risks["core_project"] = YES_NO_RISK[answers["core_project"]]
    risks["technical_team"] = YES_NO_RISK[answers["technical_team"]]
    risks["knows_core_alumni"] = YES_NO_RISK[answers["knows_core_alumni"]]
    return risks


def level_for_score(score):
    if score < LOW_LIMIT:
        return "Low"
    if score < HIGH_LIMIT:
        return "Medium"
    return "High"


def get_points(signal_and_points):
    return signal_and_points[1]


def drift_check(answers, weight_points=None):
    """
    answers: {"career_plan": one of CAREER_PLAN_OPTIONS,
              "core_course_interest": 1 to 5,
              "grade_trend": "Improving" / "Steady" / "Falling",
              "core_project": "Yes"/"No", "technical_team": "Yes"/"No",
              "knows_core_alumni": "Yes"/"No"}

    Returns a dict with:
      informed_choice: True if the student has decided on non-core and is happy (no alert)
      score: 0-100 (None for an informed choice)
      level: "Low" / "Medium" / "High" (or "Informed choice")
      contributions: {signal: points of the score}, adding up to the score
      strongest_signs: signals with risk 0.5 or more, biggest contribution first
      support: suggested help, one per strong sign
    """
    if answers["career_plan"] == INFORMED_NON_CORE_CHOICE:
        return {"informed_choice": True, "score": None, "level": "Informed choice",
                "contributions": {}, "strongest_signs": [], "support": []}

    if weight_points is None:
        weight_points = DEFAULT_DRIFT_WEIGHTS

    total_points = 0
    for signal_name in SIGNAL_NAMES:
        total_points = total_points + weight_points[signal_name]
    if total_points <= 0:
        raise ValueError("At least one sign needs a weight above 0.")

    risks = signal_risks(answers)
    contributions = {}
    score = 0.0
    for signal_name in SIGNAL_NAMES:
        weight_share = weight_points[signal_name] / total_points
        points = 100 * weight_share * risks[signal_name]
        contributions[signal_name] = points
        score = score + points

    strong_with_points = []
    for signal_name in SIGNAL_NAMES:
        if risks[signal_name] >= STRONG_SIGN and weight_points[signal_name] > 0:
            strong_with_points.append((signal_name, contributions[signal_name]))
    strong_with_points.sort(key=get_points, reverse=True)

    strongest_signs = []
    support = []
    for signal_and_points in strong_with_points:
        strongest_signs.append(signal_and_points[0])
        support.append(SUPPORT_FOR_SIGNAL[signal_and_points[0]])

    return {"informed_choice": False, "score": score, "level": level_for_score(score),
            "contributions": contributions, "strongest_signs": strongest_signs, "support": support}


# ---------------------------------------------------------------------------
# The student's own branch (v3.1)
#
# The branch does NOT change the score: two students with the same answers get the
# same score whatever their branch, so no branch is marked as "riskier" by default.
# The branch only changes what the student is shown:
#   - what a core job means for their branch (plain examples),
#   - what our research brief found for that branch (section 2.3, IIT Bombay study [1,3,4]),
#   - which technical team to try, and a Core+X path (brief, Pillar 2).
# Where the brief has no finding for a branch, we say so rather than fill the gap.
# ---------------------------------------------------------------------------
NO_FINDING_TEXT = ("Our research brief has no branch-specific finding for this branch yet. "
                   "Our survey and placement-cell data would fill this gap.")

BRANCH_PROFILES = {
    "Mechanical": {
        "core_examples": "machine and product design, manufacturing, automobiles, energy and thermal systems",
        "brief_finding": ("In an IIT Bombay study, mechanical students were split roughly equally between "
                          "core and non-core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Try a Formula Student, UAV or robotics team for one semester.",
        "core_plus_x": "Look at a Core+X path such as mechanical with simulation and data.",
    },
    "Civil": {
        "core_examples": "structures, construction, transport, water and environmental engineering",
        "brief_finding": ("In an IIT Bombay study, civil students showed a strong preference for "
                          "non-core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Join a structural design, sustainable building or infrastructure project team.",
        "core_plus_x": "Look at a Core+X path such as civil with computational design.",
    },
    "Chemical": {
        "core_examples": "process plants, refineries, chemicals, pharmaceuticals and process design",
        "brief_finding": ("In an IIT Bombay study, chemical students showed a strong preference for "
                          "non-core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Join a process simulation or plant-design project, or go on a plant visit.",
        "core_plus_x": "Look at a Core+X path such as chemical with process data.",
    },
    "Materials and Metallurgy": {
        "core_examples": "metals, alloys, polymers, semiconductors and materials testing",
        "brief_finding": ("In an IIT Bombay study, metallurgy and materials students showed a strong "
                          "preference for non-core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Join a materials characterisation or lab research project.",
        "core_plus_x": "Look at a Core+X path such as materials with computational modelling and data.",
    },
    "Electrical": {
        "core_examples": "power systems, electronics, chips, communication and control",
        "brief_finding": ("In an IIT Bombay study, electrical students showed one of the strongest "
                          "preferences for core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Try an electronics, solar car or robotics team for one semester.",
        "core_plus_x": "Look at a Core+X path such as electrical with embedded systems and data.",
    },
    "Computer Science": {
        "core_examples": "software, systems, algorithms, data and AI (for computer science these are core)",
        "brief_finding": ("In an IIT Bombay study, computer science students showed the strongest "
                          "preference for core jobs."),
        "brief_source": "Research brief section 2.3, sources [1,3]",
        "team_suggestion": "Try a systems, open-source or research project team.",
        "core_plus_x": "Look at research or product-building projects in your field.",
    },
    "Textile": {
        "core_examples": "fibres, fabrics, textile manufacturing and technical textiles",
        "brief_finding": NO_FINDING_TEXT,
        "brief_source": "",
        "team_suggestion": "Join a textile or fibre lab project, or go on an industry visit.",
        "core_plus_x": "Look at a Core+X path such as textiles with materials data or manufacturing analytics.",
    },
    "Production and Industrial": {
        "core_examples": "manufacturing systems, operations, quality and supply chains",
        "brief_finding": NO_FINDING_TEXT,
        "brief_source": "",
        "team_suggestion": "Join a manufacturing or operations improvement project.",
        "core_plus_x": "Look at a Core+X path such as production with data and automation.",
    },
    "Aerospace": {
        "core_examples": "aircraft, spacecraft, propulsion and flight systems",
        "brief_finding": NO_FINDING_TEXT,
        "brief_source": "",
        "team_suggestion": "Try a UAV, rocketry or aero-design team for one semester.",
        "core_plus_x": "Look at a Core+X path such as aerospace with simulation and data.",
    },
    "Other": {
        "core_examples": "jobs that directly use what your branch teaches",
        "brief_finding": NO_FINDING_TEXT,
        "brief_source": "",
        "team_suggestion": "Try a technical team or club linked to your field for one semester.",
        "core_plus_x": "Look at a Core+X path that joins your field with data or computing skills.",
    },
}

BRANCH_OPTIONS = list(BRANCH_PROFILES.keys())

CORE_DEFINITION = ("A core job is one directly related to the branch you studied, for example a civil "
                   "graduate in a civil role. Anything else is non-core (research brief section 2.1, "
                   "IIT Bombay study [1]). The line is not always sharp: a mechanical graduate writing "
                   "simulation software is arguably core-adjacent.")


def personalise_for_branch(result, branch):
    """
    Add branch-specific information and help to a drift_check result.
    The score, level and contributions are NOT changed.
    """
    profile = BRANCH_PROFILES.get(branch, BRANCH_PROFILES["Other"])
    personalised = dict(result)
    personalised["branch"] = branch
    personalised["core_examples"] = profile["core_examples"]
    personalised["brief_finding"] = profile["brief_finding"]
    personalised["brief_source"] = profile["brief_source"]

    if result["informed_choice"]:
        return personalised

    branch_support = []
    for index in range(len(result["strongest_signs"])):
        signal_name = result["strongest_signs"][index]
        if signal_name == "technical_team":
            branch_support.append(profile["team_suggestion"])
        else:
            branch_support.append(result["support"][index])
    if "career_plan" in result["strongest_signs"]:
        branch_support.append(profile["core_plus_x"])
    personalised["support"] = branch_support
    return personalised
