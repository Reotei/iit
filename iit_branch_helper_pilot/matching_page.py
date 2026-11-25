"""
matching_page.py — Internship matching page (proposed design, demo with made-up data).
The algorithm itself is in matching.py.

v3.1: every project says which branches it is open to, and the person using the page
can add themselves (their branch, the projects they want, where each company would
rank them) and see what they would get.
"""

import html

import pandas as pd
import streamlit as st

import ui
from matching import (
    run_matching, find_blocking_pairs, explain_student_result, position_in_list,
    projects_open_to_branch, add_student_to_demo, YOU, PLACE_OPTIONS,
    DEMO_PROJECTS, DEMO_PROJECT_BRANCHES, DEMO_STUDENT_BRANCHES,
    DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS,
)
from drift import BRANCH_OPTIONS

st.title("Core internship matching")
st.markdown(
    '<p class="hero-text">Students rank the core projects they want. Core companies rank the students '
    'they want and say how many places they have. The algorithm pairs them so that no student and '
    'company would both rather be with each other.</p>',
    unsafe_allow_html=True,
)
st.markdown(ui.proposed_notice_html(
    "<b>Proposed design, shown with made-up data.</b> Every student and company below is fictional. "
    "A real version needs core companies to take part through the placement cell. It addresses the "
    "lack of core internships in our research brief (driver D4, hypothesis H4)."
), unsafe_allow_html=True)

st.subheader("How it works")
st.markdown(
    "1. Every unplaced student applies to the best project on their list they have not tried yet.\n"
    "2. Each project keeps its best applicants, up to its number of places, and turns down the rest. "
    "A student it did not rank is always turned down.\n"
    "3. Turned-down students apply to their next choice. A project can swap a held student for one it "
    "ranks higher, so holding is only temporary.\n"
    "4. It stops when no unplaced student has a project left to try.\n\n"
    "This is the deferred-acceptance algorithm (Gale and Shapley). JoSAA seat allocation uses the same idea. "
    "Each project is open only to the branches it needs, so students apply to projects in their own field."
)

# ---------------------------------------------------------------------------
# Add yourself
# ---------------------------------------------------------------------------
st.subheader("Add yourself to the demo")
add_yourself = st.toggle("Add me as a student", value=False)

your_projects = []
your_places = {}
your_branch = None
if add_yourself:
    your_branch = st.selectbox("Your branch", BRANCH_OPTIONS, index=0, key="match_branch")
    open_projects = projects_open_to_branch(your_branch, DEMO_PROJECT_BRANCHES)
    if len(open_projects) == 0:
        st.info("None of the demo projects is open to " + your_branch + ". In a real round, the placement "
                "cell would bring in projects for every core branch.")
    else:
        your_projects = st.multiselect(
            "Projects you want, in order of preference (pick your first choice first)",
            open_projects, default=[], key="match_projects",
            help="Only projects open to your branch are listed.")
        for project_name in your_projects:
            your_places[project_name] = st.radio(
                "Where would " + project_name + " rank you?", PLACE_OPTIONS, index=1, horizontal=True,
                key="place_" + project_name)
        if len(your_projects) == 0:
            st.caption("Pick at least one project to join the matching.")

# ---------------------------------------------------------------------------
# Demo inputs
# ---------------------------------------------------------------------------
st.subheader("Demo inputs")
st.caption("Change the number of places to see how the result moves.")
project_capacities = {}
capacity_columns = st.columns(len(DEMO_PROJECTS))
project_names = list(DEMO_PROJECTS.keys())
for project_index in range(len(project_names)):
    project_name = project_names[project_index]
    with capacity_columns[project_index]:
        project_capacities[project_name] = st.number_input(
            project_name, min_value=0, max_value=5, value=DEMO_PROJECTS[project_name], step=1,
            key="places_" + project_name)

student_preferences = DEMO_STUDENT_PREFERENCES
project_rankings = DEMO_PROJECT_RANKINGS
student_branches = dict(DEMO_STUDENT_BRANCHES)
if add_yourself and len(your_projects) > 0:
    student_preferences, project_rankings = add_student_to_demo(
        DEMO_STUDENT_PREFERENCES, DEMO_PROJECT_RANKINGS, YOU, your_projects, your_places)
    student_branches[YOU] = your_branch

input_columns = st.columns(2, gap="large")
with input_columns[0]:
    st.markdown("**What each student wants (best first)**")
    student_lines = []
    for student_name in student_preferences:
        choices = student_preferences[student_name]
        student_lines.append("- **" + student_name + "** (" + student_branches[student_name] + "): "
                             + " → ".join(choices))
    st.markdown("\n".join(student_lines))
with input_columns[1]:
    st.markdown("**Who each project wants (best first)**")
    project_lines = []
    for project_name in project_rankings:
        project_lines.append("- **" + project_name + "**, open to " + ", ".join(DEMO_PROJECT_BRANCHES[project_name])
                             + ": " + " → ".join(project_rankings[project_name]))
    st.markdown("\n".join(project_lines))

# ---------------------------------------------------------------------------
# Run and show the result
# ---------------------------------------------------------------------------
assignment, rounds_log = run_matching(student_preferences, project_rankings, project_capacities)
blocking_pairs = find_blocking_pairs(assignment, student_preferences, project_rankings, project_capacities)

matched_count = 0
first_choice_count = 0
for student_name in assignment:
    if assignment[student_name] is not None:
        matched_count = matched_count + 1
        if position_in_list(assignment[student_name], student_preferences[student_name]) == 0:
            first_choice_count = first_choice_count + 1
total_places = 0
for project_name in project_capacities:
    total_places = total_places + project_capacities[project_name]

st.subheader("Result")
if YOU in assignment:
    your_result_text = explain_student_result(YOU, assignment, student_preferences)
    st.markdown('<div class="note-box"><b>Your result.</b> ' + html.escape(your_result_text) + '</div>',
                unsafe_allow_html=True)

st.markdown(ui.stat_cards_html([
    (str(matched_count) + " of " + str(len(assignment)), "students matched"),
    (str(first_choice_count), "got their first choice"),
    (str(total_places), "places on offer"),
    (str(len(rounds_log)), "rounds to finish"),
]), unsafe_allow_html=True)

if len(blocking_pairs) == 0:
    st.markdown(ui.note_html("Stable: checked every student and project, and no pair would both rather "
                             "be together than keep what they got."), unsafe_allow_html=True)
else:
    pair_texts = []
    for student_name, project_name in blocking_pairs:
        pair_texts.append(student_name + " and " + project_name)
    st.error("Not stable. These pairs would both rather be together: " + "; ".join(pair_texts))

result_rows = []
for student_name in assignment:
    project_name = assignment[student_name]
    if project_name is None:
        project_text = "Not matched"
    else:
        project_text = project_name
    result_rows.append({"Student": student_name, "Branch": student_branches[student_name],
                        "Matched to": project_text,
                        "Why": explain_student_result(student_name, assignment, student_preferences)})
result_table = pd.DataFrame(result_rows).set_index("Student")
st.table(result_table)   # st.table wraps long text instead of cutting it off

with st.expander("See every round (" + str(len(rounds_log)) + ")"):
    for round_index in range(len(rounds_log)):
        st.markdown("**Round " + str(round_index + 1) + "**")
        for event_text in rounds_log[round_index]:
            st.markdown("- " + event_text)

st.caption("Unmatched students would get help finding a core project outside the matching round, "
           "such as an industry studio course or a faculty research project. Nothing on this page is saved.")
