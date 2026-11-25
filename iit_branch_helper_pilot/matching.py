"""
matching.py — core internship matching (PROPOSED DESIGN, demo data only).

The problem (research brief, driver D4 and hypothesis H4): few students get a core
internship, so they build no core portfolio and get no core offer.

The idea: students rank the core projects they want, and each core project ranks the
students it wants and has a fixed number of places. We pair them with the
student-proposing "deferred acceptance" algorithm (Gale and Shapley, 1962), in its
version with capacities. JoSAA seat allocation is built on the same idea.

How it works, in plain words:
  1. Every unplaced student applies to the best project on their list they have not
     tried yet.
  2. Each project looks at everyone it is holding plus the new applicants, keeps the
     best ones up to its number of places (by its own ranking), and turns down the rest.
     A student the project did not rank at all is always turned down.
  3. Turned-down students go back to step 1 with their next choice.
  4. Stop when no unplaced student has any project left to try.

Holding is only temporary ("deferred"): a project can drop a student it was holding
if someone it ranks higher applies later. The result is STABLE: there is no student
and project that both prefer each other to what they ended up with.
find_blocking_pairs() checks that.
"""


def position_in_list(item, ordered_list):
    """Place of item in a best-first list (0 = best). Returns None if it is not in the list."""
    for index in range(len(ordered_list)):
        if ordered_list[index] == item:
            return index
    return None


def project_prefers(project_ranking, first_student, second_student):
    """True if the project ranks first_student above second_student."""
    first_position = position_in_list(first_student, project_ranking)
    second_position = position_in_list(second_student, project_ranking)
    if first_position is None:
        return False
    if second_position is None:
        return True
    return first_position < second_position


def sort_by_project_ranking(students, project_ranking):
    """Return the students in the project's order, best first (all must be on its list)."""
    students_with_position = []
    for student in students:
        students_with_position.append((position_in_list(student, project_ranking), student))
    students_with_position.sort(key=get_first_item)
    sorted_students = []
    for position_and_student in students_with_position:
        sorted_students.append(position_and_student[1])
    return sorted_students


def get_first_item(pair):
    return pair[0]


def run_matching(student_preferences, project_rankings, project_capacities):
    """
    student_preferences: {student: [project, ...]}   best first
    project_rankings:    {project: [student, ...]}   best first; unlisted students are not acceptable
    project_capacities:  {project: number of places}

    Returns:
      assignment: {student: project or None}
      rounds_log: list of rounds; each round is a list of plain-language event strings
    """
    next_choice_index = {}
    for student in student_preferences:
        next_choice_index[student] = 0

    held_students = {}
    for project in project_capacities:
        held_students[project] = []

    unplaced_students = list(student_preferences.keys())
    rounds_log = []

    while True:
        # Step 1: every unplaced student who still has choices applies to their next one
        applications = {}
        events = []
        still_unplaced = []
        for student in unplaced_students:
            choices = student_preferences[student]
            if next_choice_index[student] >= len(choices):
                still_unplaced.append(student)   # no projects left to try
                continue
            project = choices[next_choice_index[student]]
            next_choice_index[student] = next_choice_index[student] + 1
            if project not in project_capacities:
                events.append(student + " applied to " + project + ", which is not on offer.")
                still_unplaced.append(student)
                continue
            if project not in applications:
                applications[project] = []
            applications[project].append(student)
            events.append(student + " applied to " + project + ".")

        if len(applications) == 0:
            break

        # Step 2: each project keeps its best applicants up to capacity
        unplaced_students = still_unplaced
        for project in applications:
            project_ranking = project_rankings.get(project, [])
            acceptable = []
            for student in held_students[project] + applications[project]:
                if position_in_list(student, project_ranking) is None:
                    events.append(project + " turned down " + student + " (not on its list).")
                    unplaced_students.append(student)
                else:
                    acceptable.append(student)
            ordered = sort_by_project_ranking(acceptable, project_ranking)
            places = project_capacities[project]
            kept = ordered[:places]
            turned_down = ordered[places:]
            for student in turned_down:
                events.append(project + " turned down " + student + " (full with students it ranks higher).")
                unplaced_students.append(student)
            held_students[project] = kept

        rounds_log.append(events)

    assignment = {}
    for student in student_preferences:
        assignment[student] = None
    for project in held_students:
        for student in held_students[project]:
            assignment[student] = project
    return assignment, rounds_log


def find_blocking_pairs(assignment, student_preferences, project_rankings, project_capacities):
    """
    A blocking pair is a student and a project that would both rather be together:
    the student prefers the project to what they got, and the project either has a
    free place or ranks the student above someone it took.
    An empty list means the matching is stable.
    """
    students_at_project = {}
    for project in project_capacities:
        students_at_project[project] = []
    for student in assignment:
        if assignment[student] is not None:
            students_at_project[assignment[student]].append(student)

    blocking_pairs = []
    for student in student_preferences:
        choices = student_preferences[student]
        current_project = assignment[student]
        if current_project is None:
            better_projects = choices
        else:
            better_projects = choices[:position_in_list(current_project, choices)]
        for project in better_projects:
            if project not in project_capacities:
                continue
            project_ranking = project_rankings.get(project, [])
            if position_in_list(student, project_ranking) is None:
                continue   # the project does not want this student at all
            taken = students_at_project[project]
            if len(taken) < project_capacities[project]:
                blocking_pairs.append((student, project))
                continue
            for other_student in taken:
                if project_prefers(project_ranking, student, other_student):
                    blocking_pairs.append((student, project))
                    break
    return blocking_pairs


def explain_student_result(student, assignment, student_preferences):
    """One plain sentence for one student's result."""
    project = assignment[student]
    choices = student_preferences[student]
    if project is None:
        if len(choices) == 0:
            return "Not matched: listed no projects."
        return ("Not matched: every project on the list filled with students it ranked higher, "
                "or did not list this student.")
    choice_number = position_in_list(project, choices) + 1
    return "Got choice " + str(choice_number) + " of " + str(len(choices)) + ": " + project + "."


# ---------------------------------------------------------------------------
# Demo data: MADE UP. Students and companies are fictional, for showing how it works.
# Each project is open to some branches, and every demo student only lists projects
# open to their own branch.
# ---------------------------------------------------------------------------
DEMO_PROJECTS = {
    "Gearbox design (Demo Company 1)": 2,
    "Process plant data (Demo Company 2)": 1,
    "Bridge sensor study (Demo Company 3)": 1,
    "EV battery cooling (Demo Company 4)": 2,
}

DEMO_PROJECT_BRANCHES = {
    "Gearbox design (Demo Company 1)": ["Mechanical", "Production and Industrial"],
    "Process plant data (Demo Company 2)": ["Chemical"],
    "Bridge sensor study (Demo Company 3)": ["Civil"],
    "EV battery cooling (Demo Company 4)": ["Mechanical", "Electrical"],
}

DEMO_STUDENT_BRANCHES = {
    "Student A": "Mechanical",
    "Student B": "Mechanical",
    "Student C": "Chemical",
    "Student D": "Civil",
    "Student E": "Electrical",
    "Student F": "Mechanical",
    "Student G": "Civil",
    "Student H": "Chemical",
}

DEMO_STUDENT_PREFERENCES = {
    "Student A": ["EV battery cooling (Demo Company 4)", "Gearbox design (Demo Company 1)"],
    "Student B": ["EV battery cooling (Demo Company 4)", "Gearbox design (Demo Company 1)"],
    "Student C": ["Process plant data (Demo Company 2)"],
    "Student D": ["Bridge sensor study (Demo Company 3)"],
    "Student E": ["EV battery cooling (Demo Company 4)"],
    "Student F": ["Gearbox design (Demo Company 1)", "EV battery cooling (Demo Company 4)"],
    "Student G": ["Bridge sensor study (Demo Company 3)"],
    "Student H": ["Process plant data (Demo Company 2)"],
}

DEMO_PROJECT_RANKINGS = {
    "Gearbox design (Demo Company 1)": ["Student F", "Student B", "Student A"],
    "Process plant data (Demo Company 2)": ["Student C", "Student H"],
    "Bridge sensor study (Demo Company 3)": ["Student G", "Student D"],
    "EV battery cooling (Demo Company 4)": ["Student E", "Student A", "Student B", "Student F"],
}


# ---------------------------------------------------------------------------
# "Add yourself" (v3.1): put the person using the page into the demo
# ---------------------------------------------------------------------------
YOU = "You"
PLACE_OPTIONS = ["Top of its list", "Middle of its list", "Bottom of its list"]


def projects_open_to_branch(branch, project_branches):
    """Projects that accept students from this branch, in the demo's order."""
    open_projects = []
    for project in project_branches:
        if branch in project_branches[project]:
            open_projects.append(project)
    return open_projects


def insert_into_ranking(ranking, student, place_label):
    """Return a NEW ranking with the student placed at the top, middle or bottom."""
    new_ranking = list(ranking)
    if place_label == "Top of its list":
        insert_at = 0
    elif place_label == "Middle of its list":
        insert_at = len(new_ranking) // 2
    else:
        insert_at = len(new_ranking)
    new_ranking.insert(insert_at, student)
    return new_ranking


def add_student_to_demo(student_preferences, project_rankings, new_student, chosen_projects, place_by_project):
    """
    Return NEW copies of the demo data with one more student.
    chosen_projects: the new student's projects, best first.
    place_by_project: {project: one of PLACE_OPTIONS}, where each project would rank them.
    The original dictionaries are not changed.
    """
    new_preferences = {}
    for student in student_preferences:
        new_preferences[student] = list(student_preferences[student])
    new_preferences[new_student] = list(chosen_projects)

    new_rankings = {}
    for project in project_rankings:
        if project in place_by_project:
            new_rankings[project] = insert_into_ranking(project_rankings[project], new_student,
                                                        place_by_project[project])
        else:
            new_rankings[project] = list(project_rankings[project])
    return new_preferences, new_rankings
