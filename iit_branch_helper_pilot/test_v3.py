"""
test_v3.py — tests for internship matching (matching.py) and the drift check (drift.py).

Run:  python test_v3.py
Each test prints PASS or raises an AssertionError with what went wrong.
"""

import itertools
import random

from matching import (
    run_matching, find_blocking_pairs, position_in_list,
    DEMO_PROJECTS, DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS,
    DEMO_PROJECT_BRANCHES, DEMO_STUDENT_BRANCHES, projects_open_to_branch,
    insert_into_ranking, add_student_to_demo, YOU,
)
from drift import (
    drift_check, INFORMED_NON_CORE_CHOICE, SIGNAL_NAMES,
    BRANCH_OPTIONS, BRANCH_PROFILES, NO_FINDING_TEXT, personalise_for_branch,
)
import copy


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def capacities_respected(assignment, capacities):
    for project in capacities:
        taken = 0
        for student in assignment:
            if assignment[student] == project:
                taken = taken + 1
        if taken > capacities[project]:
            return False
    return True


def only_acceptable_pairs(assignment, student_preferences, project_rankings):
    for student in assignment:
        project = assignment[student]
        if project is None:
            continue
        if project not in student_preferences[student]:
            return False
        if student not in project_rankings[project]:
            return False
    return True


def all_matchings(students, projects):
    """Every way to give each student one project or nothing (for tiny brute-force checks)."""
    options = list(projects) + [None]
    for combination in itertools.product(options, repeat=len(students)):
        matching = {}
        for index in range(len(students)):
            matching[students[index]] = combination[index]
        yield matching


def choice_rank(student, project, student_preferences):
    """Smaller is better; unmatched is worst."""
    if project is None:
        return len(student_preferences[student]) + 1
    return position_in_list(project, student_preferences[student])


def random_instance(random_generator, student_count, project_count):
    students = ["S" + str(number) for number in range(student_count)]
    projects = ["P" + str(number) for number in range(project_count)]
    student_preferences = {}
    for student in students:
        list_length = random_generator.randint(0, project_count)
        student_preferences[student] = random_generator.sample(projects, list_length)
    project_rankings = {}
    capacities = {}
    for project in projects:
        list_length = random_generator.randint(0, student_count)
        project_rankings[project] = random_generator.sample(students, list_length)
        capacities[project] = random_generator.randint(0, 2)
    return students, projects, student_preferences, project_rankings, capacities


def test_demo_is_stable_and_valid():
    assignment, rounds_log = run_matching(DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS, DEMO_PROJECTS)
    assert find_blocking_pairs(assignment, DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS, DEMO_PROJECTS) == []
    assert capacities_respected(assignment, DEMO_PROJECTS)
    assert only_acceptable_pairs(assignment, DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS)
    matched_count = 0
    for student in assignment:
        if assignment[student] is not None:
            matched_count = matched_count + 1
    print("PASS  M1 demo: stable, places respected, " + str(matched_count) + " of "
          + str(len(assignment)) + " matched in " + str(len(rounds_log)) + " rounds")
    for student in assignment:
        print("      " + student + " -> " + str(assignment[student]))


def test_hand_worked_example():
    # Classic case: both students want X first; X has 1 place and prefers B.
    student_preferences = {"A": ["X", "Y"], "B": ["X", "Y"]}
    project_rankings = {"X": ["B", "A"], "Y": ["A", "B"]}
    capacities = {"X": 1, "Y": 1}
    assignment, _ = run_matching(student_preferences, project_rankings, capacities)
    assert assignment == {"A": "Y", "B": "X"}, assignment
    print("PASS  M2 hand-worked case: X takes B (ranked higher), A falls to Y")


def test_unlisted_student_never_placed():
    student_preferences = {"A": ["X"]}
    project_rankings = {"X": []}
    capacities = {"X": 3}
    assignment, _ = run_matching(student_preferences, project_rankings, capacities)
    assert assignment == {"A": None}
    print("PASS  M3 a project never takes a student it did not rank, even with free places")


def test_zero_capacity():
    assignment, _ = run_matching({"A": ["X"]}, {"X": ["A"]}, {"X": 0})
    assert assignment == {"A": None}
    print("PASS  M4 a project with 0 places takes nobody")


def test_against_brute_force():
    random_generator = random.Random(7)
    checked = 0
    for _ in range(400):
        students, projects, student_preferences, project_rankings, capacities = random_instance(
            random_generator, random_generator.randint(1, 4), random_generator.randint(1, 3))
        assignment, _ = run_matching(student_preferences, project_rankings, capacities)

        assert capacities_respected(assignment, capacities)
        assert only_acceptable_pairs(assignment, student_preferences, project_rankings)
        assert find_blocking_pairs(assignment, student_preferences, project_rankings, capacities) == []

        # Student-optimal: no stable matching gives any student something better
        for other in all_matchings(students, projects):
            if not capacities_respected(other, capacities):
                continue
            if not only_acceptable_pairs(other, student_preferences, project_rankings):
                continue
            if find_blocking_pairs(other, student_preferences, project_rankings, capacities) != []:
                continue
            for student in students:
                ours = choice_rank(student, assignment[student], student_preferences)
                theirs = choice_rank(student, other[student], student_preferences)
                assert ours <= theirs, ("not student-optimal", student_preferences, project_rankings, capacities)
        checked = checked + 1
    print("PASS  M5 " + str(checked) + " random cases vs every possible matching: always stable, "
          "and every student gets their best stable option")


def test_blocking_pair_detector_catches_a_bad_matching():
    student_preferences = {"A": ["X", "Y"], "B": ["X", "Y"]}
    project_rankings = {"X": ["B", "A"], "Y": ["A", "B"]}
    capacities = {"X": 1, "Y": 1}
    bad_matching = {"A": "X", "B": "Y"}   # B and X both prefer each other
    assert find_blocking_pairs(bad_matching, student_preferences, project_rankings, capacities) == [("B", "X")]
    print("PASS  M6 the stability check catches an unstable matching (B and X)")


# ---------------------------------------------------------------------------
# Drift check
# ---------------------------------------------------------------------------
NO_RISK_ANSWERS = {"career_plan": "I want a career in my own field", "core_course_interest": 5,
                   "grade_trend": "Improving", "core_project": "Yes", "technical_team": "Yes",
                   "knows_core_alumni": "Yes"}
FULL_RISK_ANSWERS = {"career_plan": "Leaning towards a non-core job", "core_course_interest": 1,
                     "grade_trend": "Falling", "core_project": "No", "technical_team": "No",
                     "knows_core_alumni": "No"}


def test_drift_extremes():
    low = drift_check(NO_RISK_ANSWERS)
    high = drift_check(FULL_RISK_ANSWERS)
    assert abs(low["score"] - 0) < 1e-9 and low["level"] == "Low" and low["support"] == []
    assert abs(high["score"] - 100) < 1e-9 and high["level"] == "High"
    assert len(high["support"]) == len(SIGNAL_NAMES)
    print("PASS  D1 no signs -> 0 (Low, no help needed); every sign -> 100 (High, 6 suggestions)")


def test_informed_choice_gets_no_alert():
    answers = dict(FULL_RISK_ANSWERS)
    answers["career_plan"] = INFORMED_NON_CORE_CHOICE
    result = drift_check(answers)
    assert result["informed_choice"] is True and result["score"] is None and result["support"] == []
    print("PASS  D2 'decided on non-core and happy' -> no alert, even with every other sign")


def test_contributions_add_up():
    random_generator = random.Random(3)
    for _ in range(200):
        answers = {
            "career_plan": random_generator.choice(["I want a career in my own field", "Not sure yet",
                                                    "Leaning towards a non-core job"]),
            "core_course_interest": random_generator.randint(1, 5),
            "grade_trend": random_generator.choice(["Improving", "Steady", "Falling"]),
            "core_project": random_generator.choice(["Yes", "No"]),
            "technical_team": random_generator.choice(["Yes", "No"]),
            "knows_core_alumni": random_generator.choice(["Yes", "No"]),
        }
        result = drift_check(answers)
        total = 0.0
        for signal_name in SIGNAL_NAMES:
            total = total + result["contributions"][signal_name]
        assert abs(total - result["score"]) < 1e-9
        assert 0 <= result["score"] <= 100
    print("PASS  D3 200 random answer sets: score is 0-100 and equals the sum of its parts")


def test_hand_worked_drift_score():
    # Not sure (0.5 x 30%) + interest 3 (0.5 x 20%) + steady (0.25 x 15%) + no project (1 x 15%)
    # + in a team (0) + no alumni (1 x 10%) = 15 + 10 + 3.75 + 15 + 0 + 10 = 53.75 -> Medium
    answers = {"career_plan": "Not sure yet", "core_course_interest": 3, "grade_trend": "Steady",
               "core_project": "No", "technical_team": "Yes", "knows_core_alumni": "No"}
    result = drift_check(answers)
    assert abs(result["score"] - 53.75) < 1e-9, result["score"]
    assert result["level"] == "Medium"
    assert result["strongest_signs"] == ["career_plan", "core_project", "core_course_interest",
                                         "knows_core_alumni"], result["strongest_signs"]
    print("PASS  D4 hand-worked example scores 53.75 (Medium), strongest signs in the right order")


# ---------------------------------------------------------------------------
# v3.1: branch input
# ---------------------------------------------------------------------------
def test_branch_never_changes_drift_score():
    random_generator = random.Random(11)
    for _ in range(100):
        answers = {
            "career_plan": random_generator.choice(["I want a career in my own field", "Not sure yet",
                                                    "Leaning towards a non-core job"]),
            "core_course_interest": random_generator.randint(1, 5),
            "grade_trend": random_generator.choice(["Improving", "Steady", "Falling"]),
            "core_project": random_generator.choice(["Yes", "No"]),
            "technical_team": random_generator.choice(["Yes", "No"]),
            "knows_core_alumni": random_generator.choice(["Yes", "No"]),
        }
        base_result = drift_check(answers)
        for branch in BRANCH_OPTIONS:
            branch_result = personalise_for_branch(base_result, branch)
            assert branch_result["score"] == base_result["score"]
            assert branch_result["level"] == base_result["level"]
            assert branch_result["contributions"] == base_result["contributions"]
            assert len(branch_result["support"]) >= len(base_result["support"])
    print("PASS  B1 100 answer sets x " + str(len(BRANCH_OPTIONS))
          + " branches: the branch never changes the score, level or its parts")


def test_branch_profiles_complete_and_honest():
    required_keys = ["core_examples", "brief_finding", "brief_source", "team_suggestion", "core_plus_x"]
    for branch in BRANCH_OPTIONS:
        profile = BRANCH_PROFILES[branch]
        for key in required_keys:
            assert key in profile, (branch, key)
        if profile["brief_finding"] == NO_FINDING_TEXT:
            assert profile["brief_source"] == "", branch
        else:
            assert "section 2.3" in profile["brief_source"], branch
    print("PASS  B2 every branch has a full profile; every research claim names brief section 2.3, "
          "and branches without data say so")


def test_branch_specific_help():
    answers = {"career_plan": "Not sure yet", "core_course_interest": 3, "grade_trend": "Steady",
               "core_project": "No", "technical_team": "No", "knows_core_alumni": "No"}
    mechanical = personalise_for_branch(drift_check(answers), "Mechanical")
    civil = personalise_for_branch(drift_check(answers), "Civil")
    assert BRANCH_PROFILES["Mechanical"]["team_suggestion"] in mechanical["support"]
    assert BRANCH_PROFILES["Mechanical"]["core_plus_x"] in mechanical["support"]
    assert BRANCH_PROFILES["Civil"]["team_suggestion"] in civil["support"]
    informed = dict(answers)
    informed["career_plan"] = INFORMED_NON_CORE_CHOICE
    informed_result = personalise_for_branch(drift_check(informed), "Mechanical")
    assert informed_result["support"] == [] and informed_result["score"] is None
    print("PASS  B3 help is branch-specific (Formula/UAV for mechanical, structures for civil); "
          "informed choice still gets no alert")


def test_demo_respects_branches():
    for student in DEMO_STUDENT_PREFERENCES:
        for project in DEMO_STUDENT_PREFERENCES[student]:
            assert DEMO_STUDENT_BRANCHES[student] in DEMO_PROJECT_BRANCHES[project], (student, project)
    for project in DEMO_PROJECT_RANKINGS:
        for student in DEMO_PROJECT_RANKINGS[project]:
            assert DEMO_STUDENT_BRANCHES[student] in DEMO_PROJECT_BRANCHES[project], (student, project)
    assert projects_open_to_branch("Chemical", DEMO_PROJECT_BRANCHES) == ["Process plant data (Demo Company 2)"]
    assert projects_open_to_branch("Textile", DEMO_PROJECT_BRANCHES) == []
    print("PASS  B4 every demo student only lists, and is only ranked by, projects open to their branch")


def test_insert_positions():
    ranking = ["S1", "S2", "S3", "S4"]
    assert insert_into_ranking(ranking, YOU, "Top of its list") == [YOU, "S1", "S2", "S3", "S4"]
    assert insert_into_ranking(ranking, YOU, "Middle of its list") == ["S1", "S2", YOU, "S3", "S4"]
    assert insert_into_ranking(ranking, YOU, "Bottom of its list") == ["S1", "S2", "S3", "S4", YOU]
    assert ranking == ["S1", "S2", "S3", "S4"]
    print("PASS  B5 top / middle / bottom insert in the right place and leave the original list alone")


def test_add_yourself():
    original_preferences = copy.deepcopy(DEMO_STUDENT_PREFERENCES)
    original_rankings = copy.deepcopy(DEMO_PROJECT_RANKINGS)
    gearbox = "Gearbox design (Demo Company 1)"
    ev_project = "EV battery cooling (Demo Company 4)"

    # Top of the Gearbox list: You must get Gearbox (it has 2 places)
    preferences, rankings = add_student_to_demo(DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS, YOU,
                                                [gearbox], {gearbox: "Top of its list"})
    assignment, _ = run_matching(preferences, rankings, DEMO_PROJECTS)
    assert assignment[YOU] == gearbox, assignment
    assert find_blocking_pairs(assignment, preferences, rankings, DEMO_PROJECTS) == []

    # Bottom of both lists: both projects are full with students ranked higher, so You is not matched
    preferences, rankings = add_student_to_demo(DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS, YOU,
                                                [ev_project, gearbox],
                                                {ev_project: "Bottom of its list", gearbox: "Bottom of its list"})
    assignment, _ = run_matching(preferences, rankings, DEMO_PROJECTS)
    assert assignment[YOU] is None, assignment
    assert find_blocking_pairs(assignment, preferences, rankings, DEMO_PROJECTS) == []

    assert DEMO_STUDENT_PREFERENCES == original_preferences
    assert DEMO_PROJECT_RANKINGS == original_rankings
    print("PASS  B6 adding yourself: top of a list wins a place, bottom of full lists does not; "
          "always stable; demo data left unchanged")


test_branch_never_changes_drift_score()
test_branch_profiles_complete_and_honest()
test_branch_specific_help()
test_demo_respects_branches()
test_insert_positions()
test_add_yourself()
test_demo_is_stable_and_valid()
test_hand_worked_example()
test_unlisted_student_never_placed()
test_zero_capacity()
test_against_brute_force()
test_blocking_pair_detector_catches_a_bad_matching()
test_drift_extremes()
test_informed_choice_gets_no_alert()
test_contributions_add_up()
test_hand_worked_drift_score()
print("All v3 tests passed.")
