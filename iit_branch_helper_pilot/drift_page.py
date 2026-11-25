"""
drift_page.py — Drift check page (proposed design). The scoring itself is in drift.py.
"""

import html

import altair as alt
import pandas as pd
import streamlit as st

import ui
from drift import (
    drift_check, CAREER_PLAN_OPTIONS, GRADE_TREND_OPTIONS, YES_NO_OPTIONS,
    SIGNAL_NAMES, SIGNAL_LABELS, DEFAULT_DRIFT_WEIGHTS, LOW_LIMIT, HIGH_LIMIT,
    BRANCH_OPTIONS, CORE_DEFINITION, personalise_for_branch,
)

st.title("Are you drifting away from your field?")
st.markdown(
    '<p class="hero-text">A two-minute check for students in years 1 and 2 of a core branch. It looks for '
    'early signs that you are moving away from your field without really choosing to, and suggests help '
    'while there is still time.</p>',
    unsafe_allow_html=True,
)
st.markdown(ui.proposed_notice_html(
    "<b>Proposed design, not validated.</b> The weights are our team's assumptions until our survey and a "
    "pilot test them (research brief hypotheses H2, H4 and H6). Your answers are used only on this page and "
    "are not saved."
), unsafe_allow_html=True)

with st.expander("What do we mean by a \"core\" job?"):
    st.markdown(CORE_DEFINITION)

with st.form("drift_form"):
    branch = st.selectbox("Your branch", BRANCH_OPTIONS, index=0,
                          help="Used only to show facts and help for your branch. It does not change your score.")
    form_columns = st.columns(2, gap="large")
    with form_columns[0]:
        career_plan = st.radio("Which is closest to your plan after graduating?", CAREER_PLAN_OPTIONS,
                               index=1)
        core_course_interest = st.select_slider(
            "How interested are you in your core courses this semester? (1 = not at all, 5 = a lot)",
            options=[1, 2, 3, 4, 5], value=3)
        grade_trend = st.radio("Your core-course grades compared with last semester", GRADE_TREND_OPTIONS,
                               index=1, horizontal=True)
    with form_columns[1]:
        core_project = st.radio("Have you done a project or internship in your own field?", YES_NO_OPTIONS,
                                index=1, horizontal=True)
        technical_team = st.radio("Are you in a technical team or club linked to your field?", YES_NO_OPTIONS,
                                  index=1, horizontal=True)
        knows_core_alumni = st.radio("Do you know a senior or alumnus who works in your field?", YES_NO_OPTIONS,
                                     index=1, horizontal=True)
    check_pressed = st.form_submit_button("Check", type="primary")
if check_pressed:
    st.session_state["drift_checked"] = True

with st.expander("How this check works and the rules that keep it fair"):
    weight_texts = []
    total_points = 0
    for signal_name in SIGNAL_NAMES:
        total_points = total_points + DEFAULT_DRIFT_WEIGHTS[signal_name]
    for signal_name in SIGNAL_NAMES:
        share = round(100 * DEFAULT_DRIFT_WEIGHTS[signal_name] / total_points)
        weight_texts.append(SIGNAL_LABELS[signal_name] + " " + str(share) + "%")
    st.markdown(
        "Each answer becomes a risk from 0 to 1. The score is the weighted sum of those risks, out of 100: "
        "the same method as the branch tool. Weights (team assumption): " + ", ".join(weight_texts) + ".\n\n"
        "- If you have decided on a non-core career and are happy with it, there is no alert.\n"
        "- Only your own answers are used: no grades from college systems, and no category, gender, income "
        "or home state.\n"
        "- Your branch only changes the facts and help you see, never the score, so no branch is marked as "
        "riskier by default.\n"
        "- The result is for you only. In a real pilot it would be used to offer help, never for grades or "
        "rankings, and only with your consent.\n"
        "- Nothing you enter is saved."
    )

if st.session_state.get("drift_checked") is not True:
    st.info("Answer the questions above and press Check to see your result.")
    st.stop()

answers = {
    "career_plan": career_plan,
    "core_course_interest": core_course_interest,
    "grade_trend": grade_trend,
    "core_project": core_project,
    "technical_team": technical_team,
    "knows_core_alumni": knows_core_alumni,
}
result = personalise_for_branch(drift_check(answers), branch)

st.subheader("Your result")
finding_html = "<b>" + html.escape(branch) + ".</b> Core jobs for you: " + html.escape(result["core_examples"]) + ".<br>"
finding_html = finding_html + html.escape(result["brief_finding"])
if result["brief_source"] != "":
    finding_html = finding_html + " <i>(" + html.escape(result["brief_source"]) + ")</i>"
st.markdown('<div class="note-box">' + finding_html + '</div>', unsafe_allow_html=True)

if result["informed_choice"]:
    st.markdown(ui.note_html(
        "You have made an informed choice, so there is no alert. Our project is about making sure leaving "
        "your field is a choice, not a default, and yours is a choice. Good luck!"), unsafe_allow_html=True)
else:
    score_text = str(int(round(result["score"])))
    st.markdown(ui.stat_cards_html([
        (result["level"], "drift risk"),
        (score_text + " / 100", "risk score"),
        (str(len(result["strongest_signs"])), "strong signs found"),
    ]), unsafe_allow_html=True)
    st.caption("Low below " + str(LOW_LIMIT) + ", Medium " + str(LOW_LIMIT) + " to " + str(HIGH_LIMIT)
               + ", High " + str(HIGH_LIMIT) + " or more. Higher means more signs of drifting away.")

    if len(result["support"]) > 0:
        st.markdown("**Help we would offer you**")
        for support_text in result["support"]:
            st.markdown("- " + support_text)
    else:
        st.markdown(ui.note_html("No strong signs of drift. Keep doing what you are doing."),
                    unsafe_allow_html=True)

    contribution_rows = []
    for signal_name in SIGNAL_NAMES:
        contribution_rows.append({"Sign": SIGNAL_LABELS[signal_name],
                                  "Points": round(result["contributions"][signal_name], 1)})
    contribution_table = pd.DataFrame(contribution_rows)
    st.markdown("**What makes up your score**")
    contribution_chart = alt.Chart(contribution_table).mark_bar(color=ui.ACCENT_TEAL, cornerRadiusEnd=3).encode(
        x=alt.X("Points:Q", title="Points of the risk score", scale=alt.Scale(domain=[0, 30])),
        y=alt.Y("Sign:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240, labelOverlap=False)),
        tooltip=["Sign", "Points"],
    ).properties(height=220)
    st.altair_chart(contribution_chart, width="stretch")
