"""
app.py — Streamlit interface for the IIT branch-choice helper.

Run with:   streamlit run app.py

Page flow:
  Sidebar  -> rank and seat pool (stays visible)
  Tab 1    -> interest in each branch group (required)
  Tab 2    -> strengths, money, location, family
  Tab 3    -> how much each factor matters (weights)
  Tab 4    -> the ranked choice list, details for one option, comparison, download
"""

import os

import altair as alt
import pandas as pd
import streamlit as st

# The data files are read by relative path ("data/...", "static/..."). Hosting services
# do not always start the app from this folder, so move into it before loading anything.
APP_FOLDER = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_FOLDER)

from loader import load_all_closing_ranks
from feasibility import (
    feasibility_for_student, load_calibration, closing_rank_by_year, YEARS_TO_USE,
)
from scoring import (
    rank_options, load_institute_table, net_tuition_per_year, ALL_BRANCH_GROUPS,
    FACTOR_NAMES, DEFAULT_IMPORTANCE, FACTORS_WITHOUT_DATA, build_demand_table, SUBJECTS, INCOME_BANDS,
)
import ui
from stability import check_stability, LABEL_STABLE, LABEL_DEPENDS, LABEL_FRAGILE


# ---------------------------------------------------------------------------
# Words shown on the page
# ---------------------------------------------------------------------------
GROUP_DESCRIPTIONS = {
    "Computing": "Software, algorithms, data and AI.",
    "Electrical and Electronics": "Circuits, chips, power systems and communication.",
    "Aerospace": "Aircraft, spacecraft, flight and propulsion.",
    "Mechanical and Production": "Machines, engines, manufacturing and physical product design.",
    "Civil and Infrastructure": "Buildings, bridges, water, transport and the environment.",
    "Biotech and Bio-engineering": "Living systems, medicine and biomedical devices.",
    "Chemical and Process": "Turning raw materials into fuels, chemicals and products at scale.",
    "Materials and Metallurgy": "Metals, ceramics, polymers and new materials.",
    "Earth, Mining and Energy": "Geology, mining, petroleum, ocean and energy systems.",
    "Textile": "Fibres, fabrics and how they are made.",
    "Architecture and Design": "Buildings and spaces, products and visual design.",
    "Pure and Applied Sciences": "Physics, chemistry, maths and economics, often leading to research.",
    "Agriculture and Food": "Farm systems, food processing and agri-tech.",
    "General and Interdisciplinary": "Broad engineering foundations before you specialise.",
}

INTEREST_LEVELS = ["Not for me", "Unlikely", "Not sure", "Interested", "Very interested"]
STRENGTH_LEVELS = ["Weak", "Below average", "Average", "Good", "Strong"]
IMPORTANCE_LEVELS = {"Ignore": 0, "A little": 5, "Some": 10, "A lot": 20, "Most of all": 30}

SUBJECT_LABELS = {
    "physics": "Physics",
    "chemistry": "Chemistry",
    "mathematics": "Mathematics",
    "biology": "Biology",
    "computing": "Coding and logic",
    "drawing_design": "Drawing and visual design",
}

FACTOR_LABELS = {
    "interest": "Interest in the branch",
    "aptitude": "Fit with your strengths",
    "career_path": "Career path fit",
    "salary_fit": "Salary",
    "institute_quality": "Institute ranking",
    "demand": "How sought-after it is",
    "flexibility": "Flexibility to switch",
    "location": "Location",
    "finance": "Fees and early earning",
    "family": "Family's view",
    "campus_life": "Campus life",
}

FACTOR_HELP = {
    "interest": "From Step 1.",
    "aptitude": "Your subject strengths matched to what each branch uses most. The matching is our team's estimate.",
    "career_path": "Not available yet: needs branch-level placement data.",
    "salary_fit": "NIRF 2025 median salary of placed graduates, whole institute (not by branch), against your target.",
    "institute_quality": "NIRF 2025 engineering score, rescaled across IITs.",
    "demand": ("How early this program's OPEN seats filled up in 2024-2026: a lower closing rank means more top-ranked students chose it. It shows what others valued, not what suits you, so it starts low."),
    "flexibility": "Not available yet: needs each IIT's minor and branch-change rules.",
    "location": "Whether the IIT is in a region you prefer.",
    "finance": "IIT tuition after fee remission against your budget, and 4 vs 5 years if you need to earn early.",
    "family": "Your family's ratings of branch groups.",
    "campus_life": "Not available yet: needs our student survey.",
}

REGIONS = ["North", "South", "East", "West", "Central", "Northeast", "Abroad (Abu Dhabi)"]

CORE_PATTERN_NOTES = {
    "Computing": "At IIT Bombay, students in computing showed the strongest preference for jobs in their own field.",
    "Electrical and Electronics": "At IIT Bombay, electrical students leaned towards jobs in their own field.",
    "Mechanical and Production": "At IIT Bombay, mechanical students split roughly evenly between core and non-core jobs.",
    "Chemical and Process": "At IIT Bombay, chemical students mostly preferred non-core jobs (consulting, finance, IT).",
    "Civil and Infrastructure": "At IIT Bombay, civil students mostly preferred non-core jobs (consulting, finance, IT).",
    "Materials and Metallurgy": "At IIT Bombay, metallurgy and materials students mostly preferred non-core jobs.",
}
CORE_PATTERN_SOURCE = (
    "From one IIT Bombay placement study, cited in our research brief (section 2.3). 'Core' is defined "
    "differently across sources. The same study found median core and non-core salaries were similar in "
    "most branches; the visible gap is in a few very large offers."
)


# An example student, for demos and for trying the tool quickly.
EXAMPLE_STUDENT = {
    "interest": {
        "Mechanical and Production": "Very interested", "Aerospace": "Interested",
        "Computing": "Not sure", "Electrical and Electronics": "Not sure",
        "Materials and Metallurgy": "Not sure", "Civil and Infrastructure": "Unlikely",
        "Chemical and Process": "Unlikely", "Earth, Mining and Energy": "Unlikely",
        "Pure and Applied Sciences": "Unlikely", "Textile": "Not for me",
        "Biotech and Bio-engineering": "Not for me", "Architecture and Design": "Not for me",
        "Agriculture and Food": "Not for me", "General and Interdisciplinary": "Unlikely",
    },
    "subjects": {
        "physics": "Strong", "chemistry": "Below average", "mathematics": "Good",
        "biology": "Weak", "computing": "Average", "drawing_design": "Good",
    },
}


def fill_example_student():
    """Button callback: set every widget to the example student's answers."""
    for group_name in EXAMPLE_STUDENT["interest"]:
        st.session_state["interest_" + group_name] = EXAMPLE_STUDENT["interest"][group_name]
    for subject_name in EXAMPLE_STUDENT["subjects"]:
        st.session_state["subject_" + subject_name] = EXAMPLE_STUDENT["subjects"][subject_name]
    st.session_state["regions"] = ["North", "Northeast"]
    st.session_state["early_earning"] = "Yes"
    st.session_state["desired_salary"] = 15.0
    st.session_state["income_band"] = "Rs 1-5 lakh"
    st.session_state["crl_rank"] = 5000


# ---------------------------------------------------------------------------
# Data (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    closing_ranks = load_all_closing_ranks()
    institutes = load_institute_table()
    calibration = load_calibration()
    demand = build_demand_table(closing_ranks)
    return closing_ranks, institutes, calibration, demand


@st.cache_data
def cached_feasibility(category, is_female, is_pwd, crl_rank, category_rank, pwd_rank):
    closing_ranks, _, calibration, _ = load_data()
    return feasibility_for_student(closing_ranks, category, is_female, is_pwd,
                                   crl_rank, category_rank, pwd_rank, calibration)


# ---------------------------------------------------------------------------
# Page set-up
# ---------------------------------------------------------------------------
st.set_page_config(page_title="IIT Branch Choice Helper", page_icon="🎓", layout="wide")
st.markdown(ui.PAGE_STYLE, unsafe_allow_html=True)

closing_ranks, institutes, calibration, demand_table = load_data()

# ?demo=1 in the address loads the example student once (used for screenshots and talks)
if st.query_params.get("demo") == "1" and st.session_state.get("demo_loaded") is None:
    fill_example_student()
    st.session_state["demo_loaded"] = True

first_year = str(YEARS_TO_USE[0])
last_year = str(YEARS_TO_USE[-1])

st.title("Choose your IIT branch for your reasons, not just your rank")
st.markdown(
    '<p class="hero-text">Tell us your JEE Advanced rank and what matters to you. We show which IIT '
    'programs your rank can realistically get, how well each one fits your priorities, and a draft '
    'JoSAA choice list in that order.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="pilot-notice"><b>Pilot version for a student project at IIT Delhi.</b> This is not an '
    'official JoSAA or IIT tool. Chances are estimates from past years, not guarantees: check every '
    'choice on <a href="https://josaa.nic.in" target="_blank" rel="noopener">josaa.nic.in</a> before '
    'you fill it. This app does not save anything you enter; it is used only to build your list while '
    'the page is open.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: rank and seat pool
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Your rank")
    if "crl_rank" not in st.session_state:
        st.session_state["crl_rank"] = 5000
    crl_rank = st.number_input("JEE Advanced CRL (common rank)", min_value=1, step=100, key="crl_rank")
    category = st.selectbox("Category", ["OPEN", "EWS", "OBC-NCL", "SC", "ST"])
    category_rank = None
    if category != "OPEN":
        category_rank = st.number_input(category + " category rank", min_value=1, value=2000, step=50)
    gender = st.radio("Gender", ["Male", "Female"], horizontal=True)
    is_female = gender == "Female"
    is_pwd = st.checkbox("I have a PwD certificate")
    pwd_rank = None
    if is_pwd:
        pwd_rank = st.number_input("PwD rank (within your category)", min_value=1, value=100, step=10)

    st.caption(
        "OPEN seats use your CRL. Category seats use your category rank. "
        "Female candidates are also considered for female-only seats."
    )
    st.divider()
    st.button("Try an example student", on_click=fill_example_student,
              help="Fills every step with a sample student who likes mechanical engineering.")
    st.caption(
        "Chances come from how IIT closing ranks moved between years. In a test on " + last_year
        + " counselling, options marked Safe were actually got 97% of the time (92% for PwD seats). "
        "They are estimates, not guarantees."
    )

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_interests, tab_priorities, tab_weights, tab_results = st.tabs(
    ["1. Your interests", "2. Strengths and money", "3. Must-haves and weights", "4. Your choice list"]
)

# Tab 1: interests ----------------------------------------------------------
with tab_interests:
    st.subheader("How interested are you in each kind of work?")
    st.markdown('<p class="step-hint">Every group needs an answer. Pick "Not for me" for anything you '
                'would never study. If you are unsure what a branch involves, the line under it says '
                'what its graduates work on.</p>', unsafe_allow_html=True)

    interest_ratings = {}
    interest_columns = st.columns(2, gap="large")
    for group_index in range(len(ALL_BRANCH_GROUPS)):
        group_name = ALL_BRANCH_GROUPS[group_index]
        column = interest_columns[group_index % 2]
        with column:
            if "interest_" + group_name not in st.session_state:
                st.session_state["interest_" + group_name] = "Not sure"
            st.markdown('<div class="group-title">' + group_name + '</div>'
                        + '<p class="group-blurb">' + GROUP_DESCRIPTIONS[group_name] + '</p>',
                        unsafe_allow_html=True)
            chosen_level = st.select_slider(group_name, options=INTEREST_LEVELS, key="interest_" + group_name,
                                            label_visibility="collapsed")
        interest_ratings[group_name] = INTEREST_LEVELS.index(chosen_level) + 1

# Tab 2: strengths, money, location, family -------------------------------
with tab_priorities:
    st.subheader("Your strengths")
    st.markdown('<p class="step-hint">Rate yourself honestly. Leave this off if you would rather not '
                'use it.</p>', unsafe_allow_html=True)
    use_strengths = st.toggle("Use my subject strengths", value=True)
    subject_ratings = {}
    if use_strengths:
        strength_columns = st.columns(3)
        for subject_index in range(len(SUBJECTS)):
            subject_name = SUBJECTS[subject_index]
            with strength_columns[subject_index % 3]:
                if "subject_" + subject_name not in st.session_state:
                    st.session_state["subject_" + subject_name] = "Average"
                chosen_strength = st.select_slider(SUBJECT_LABELS[subject_name], options=STRENGTH_LEVELS,
                                                   key="subject_" + subject_name)
            subject_ratings[subject_name] = STRENGTH_LEVELS.index(chosen_strength) + 1

    st.subheader("Money")
    money_columns = st.columns(2, gap="large")
    with money_columns[0]:
        if "income_band" not in st.session_state:
            st.session_state["income_band"] = INCOME_BANDS[2]
        income_band = st.selectbox("Annual family income", INCOME_BANDS, key="income_band")
        tuition_budget = st.number_input("Tuition your family can pay per year (Rs)", min_value=0,
                                         value=200000, step=10000)
        yearly_tuition = net_tuition_per_year(category, is_pwd, income_band)
        st.caption("Your IIT tuition after fee remission: about " + ui.format_rupees(yearly_tuition)
                   + " per year (full tuition is Rs 2 lakh). Hostel and mess are extra and vary by IIT.")
    with money_columns[1]:
        early_earning_choice = st.radio("Do you need to start earning soon after graduating?",
                                        ["Not a factor", "No", "Yes"], horizontal=True, key="early_earning")
        if "desired_salary" not in st.session_state:
            st.session_state["desired_salary"] = 0.0
        desired_salary = st.number_input("Starting salary you hope for (Rs lakh per year, 0 to skip)",
                                         min_value=0.0, step=1.0, key="desired_salary")

    needs_early_earning = None
    if early_earning_choice == "Yes":
        needs_early_earning = True
    if early_earning_choice == "No":
        needs_early_earning = False

    st.subheader("Location")
    preferred_regions = st.multiselect("Regions you would like to study in (leave empty if it does not matter)",
                                       REGIONS, key="regions")

    st.subheader("Family")
    use_family_view = st.toggle("Include my family's view")
    family_ratings = {}
    if use_family_view:
        st.caption("Rate only the groups your family has a clear view on. The rest count as neutral.")
        family_groups = st.multiselect("Groups your family has a view on", ALL_BRANCH_GROUPS)
        family_columns = st.columns(2)
        for family_index in range(len(family_groups)):
            group_name = family_groups[family_index]
            with family_columns[family_index % 2]:
                family_level = st.select_slider("Family view: " + group_name, options=INTEREST_LEVELS,
                                                value="Interested", key="family_" + group_name)
            family_ratings[group_name] = INTEREST_LEVELS.index(family_level) + 1

# Tab 3: weights -------------------------------------------------------------
with tab_weights:
    st.subheader("Your must-haves")
    st.markdown('<p class="step-hint">Dealbreakers you will not compromise on. All are off unless you '
                'turn them on. Options that break one are removed before scoring and listed on your results '
                'with the reason, never hidden.</p>', unsafe_allow_html=True)
    must_have_columns = st.columns(2, gap="large")
    with must_have_columns[0]:
        use_fee_limit = st.toggle("Tuition limit")
        max_tuition_per_year = None
        if use_fee_limit:
            max_tuition_per_year = st.number_input("Highest yearly tuition you can accept (Rs)", min_value=0,
                                                   value=100000, step=10000, key="max_tuition")
            st.caption("Your tuition after remission is about "
                       + ui.format_rupees(net_tuition_per_year(category, is_pwd, income_band))
                       + " per year at every IIT, so this keeps all or none of them. Fees for the Abu Dhabi "
                       "campus are unknown, so those options are kept and flagged.")
        use_region_limit = st.toggle("Only these regions")
        allowed_regions = []
        if use_region_limit:
            allowed_regions = st.multiselect("Regions you will accept", REGIONS, key="allowed_regions")
    with must_have_columns[1]:
        exclude_five_year = st.toggle("4-year programs only")
        use_group_exclusion = st.toggle("Never show some branch groups")
        excluded_groups = []
        if use_group_exclusion:
            excluded_groups = st.multiselect("Branch groups to leave out", ALL_BRANCH_GROUPS, key="excluded_groups")
    must_haves = {
        "max_tuition_per_year": max_tuition_per_year,
        "allowed_regions": allowed_regions,
        "exclude_five_year": exclude_five_year,
        "excluded_groups": excluded_groups,
    }

    st.subheader("How much should each factor count?")
    st.markdown('<p class="step-hint"><b>The positions below are starting values, not a recommendation.</b> '
                'Our team set them as a guess until a student survey replaces them. Move each one to match '
                'what matters to you before you read your list. Greyed-out factors have no data yet; they '
                'keep their share, so the coverage figure on your results stays honest about what is '
                'missing.</p>', unsafe_allow_html=True)

    importance_labels = list(IMPORTANCE_LEVELS.keys())
    importance_values = {}
    weight_columns = st.columns(2, gap="large")
    for factor_index in range(len(FACTOR_NAMES)):
        factor_name = FACTOR_NAMES[factor_index]
        default_points = DEFAULT_IMPORTANCE[factor_name]
        default_label = "Some"
        for label_text in importance_labels:
            if IMPORTANCE_LEVELS[label_text] == default_points:
                default_label = label_text
        has_no_data = factor_name in FACTORS_WITHOUT_DATA
        slider_options = importance_labels
        if factor_name == "interest":
            slider_options = importance_labels[1:]   # interest is required: no "Ignore"
        with weight_columns[factor_index % 2]:
            chosen_importance = st.select_slider(FACTOR_LABELS[factor_name], options=slider_options,
                                                 value=default_label, disabled=has_no_data,
                                                 help=FACTOR_HELP[factor_name],
                                                 key="weight_" + factor_name)
        importance_values[factor_name] = IMPORTANCE_LEVELS[chosen_importance]

    total_importance = sum(importance_values.values())
    weights = {}
    for factor_name in FACTOR_NAMES:
        if total_importance > 0:
            weights[factor_name] = importance_values[factor_name] / total_importance
        else:
            weights[factor_name] = 0.0

    share_rows = []
    for factor_name in FACTOR_NAMES:
        if weights[factor_name] > 0:
            share_rows.append({"Factor": FACTOR_LABELS[factor_name],
                               "Share": round(100 * weights[factor_name]),
                               "Status": "No data yet" if factor_name in FACTORS_WITHOUT_DATA else "Used"})
    share_table = pd.DataFrame(share_rows)
    share_chart = alt.Chart(share_table).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("Share:Q", title="Share of your score (%)"),
        y=alt.Y("Factor:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
        color=alt.Color("Status:N", scale=alt.Scale(domain=["Used", "No data yet"],
                                                    range=["#1F6B50", "#C9D6CD"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Factor", "Share", "Status"],
    ).properties(height=30 * len(share_table) + 20)
    st.altair_chart(share_chart, width="stretch", height=30 * len(share_table) + 70)

# Tab 4: results -------------------------------------------------------------
with tab_results:
    student = {
        "interest_ratings": interest_ratings,
        "subject_ratings": subject_ratings,
        "family_ratings": family_ratings,
        "preferred_regions": preferred_regions,
        "needs_early_earning": needs_early_earning,
        "desired_salary_lpa": desired_salary,
        "tuition_budget_per_year": tuition_budget,
        "income_band": income_band,
        "category": category,
        "is_pwd": is_pwd,
    }

    usable_importance = 0
    for factor_name in FACTOR_NAMES:
        if factor_name not in FACTORS_WITHOUT_DATA:
            usable_importance = usable_importance + importance_values[factor_name]
    if usable_importance == 0:
        st.warning("Every factor is set to Ignore, so there is nothing to rank by. "
                   "In Step 3, give at least one factor some weight.")
        st.stop()

    feasibility_table = cached_feasibility(category, is_female, is_pwd, crl_rank, category_rank, pwd_rank)
    if len(feasibility_table) == 0 or (feasibility_table["label"] != "Out").sum() == 0:
        st.warning("No IIT program had a realistic chance at this rank in " + first_year + "-" + last_year
                   + ". Check the ranks in the sidebar: category seats need your category rank, not your CRL.")
        st.stop()

    ranked, unrated_options, warnings, removed_options = rank_options(
        feasibility_table, institutes, student, weights, demand_table, must_haves)

    if len(removed_options) > 0:
        st.markdown("**" + str(len(removed_options)) + " options removed by your must-haves.** "
                    "Open the list below to see why.")
        with st.expander("Removed by your must-haves (" + str(len(removed_options)) + ")"):
            removed_table = pd.DataFrame({
                "Institute": removed_options["institute"].apply(ui.short_institute_name),
                "Program": removed_options["branch"] + " (" + removed_options["duration_years"].astype(int).astype(str) + " yrs)",
                "Chance": removed_options["label"],
                "Why it was removed": removed_options["removed_reason"],
            })
            st.dataframe(removed_table, hide_index=True, width="stretch")

    if len(ranked) == 0:
        st.warning("Your must-haves leave no options to rank. Relax one of them in Step 3.")
        st.stop()

    # Step B: how much each recommendation depends on the exact weights
    stability_table = check_stability(ranked, weights)
    ranked = ranked.merge(stability_table, left_on="preference_rank", right_on="option_id", how="left")

    weights_unchanged = True
    for factor_name in FACTOR_NAMES:
        if importance_values[factor_name] != DEFAULT_IMPORTANCE[factor_name]:
            weights_unchanged = False
    if weights_unchanged:
        st.info("You are using the starting weights. They are our team's guess, not advice. "
                "Go to Step 3 and set how much each factor matters to you; the list will update.")

    distinct_interest_values = set(interest_ratings.values())
    if len(distinct_interest_values) == 1:
        st.info("All your interest answers are the same, so interest cannot separate your options yet. "
                "Go to Step 1 and mark what you like more and less.")
    for warning_text in warnings:
        st.warning(warning_text)

    st.subheader(str(len(ranked)) + " programs within reach, in your order of preference")
    st.markdown(ui.chance_summary_html(ranked["label"].value_counts()), unsafe_allow_html=True)
    average_coverage = ranked["coverage"].mean()
    st.caption(
        "The order follows how well each program fits your priorities. Chance never moves an option down: "
        "in JoSAA, listing a long shot high costs you nothing if you don't get it. Scores use "
        + str(round(100 * average_coverage)) + "% of your weights. The strip under each option shows "
        "past closing ranks (" + first_year + "-" + last_year + ") as a band, the median as a line, "
        "and your rank as a dot; further left is a better rank."
    )
    stable_count = int((ranked["stability_label"] == LABEL_STABLE).sum())
    st.markdown(ui.note_html(
        "Stable pick = stays in your top 10 in 80%+ of 500 re-runs with every weight changed by up to 20%. "
        "Depends on your weights = 40-80%. Fragile = below 40%. "
        + str(stable_count) + " of your options are stable picks."), unsafe_allow_html=True)

    filter_columns = st.columns([2, 3])
    with filter_columns[0]:
        chosen_labels = st.multiselect("Show", ["Safe", "Likely", "Reach"], default=["Safe", "Likely", "Reach"])
    with filter_columns[1]:
        chosen_groups = st.multiselect("Only these branch groups (empty shows all)", ALL_BRANCH_GROUPS)

    ranked["list_position"] = range(1, len(ranked) + 1)
    label_is_chosen = ranked["label"].isin(chosen_labels)
    if len(chosen_groups) > 0:
        group_is_chosen = ranked["branch_group"].isin(chosen_groups)
    else:
        group_is_chosen = pd.Series(True, index=ranked.index)
    shown = ranked[label_is_chosen & group_is_chosen]

    if len(shown) == 0:
        st.info("Nothing matches these filters. Clear them to see your full list.")
    else:
        rows_per_page = 15
        page_count = (len(shown) + rows_per_page - 1) // rows_per_page
        page_number = 1
        if page_count > 1:
            page_columns = st.columns([1, 4])
            with page_columns[0]:
                page_number = st.number_input("Page", min_value=1, max_value=page_count, value=1, step=1)
        start_index = (page_number - 1) * rows_per_page
        page_rows = shown.iloc[start_index:start_index + rows_per_page]
        first_position = int(page_rows["list_position"].iloc[0])
        st.markdown(ui.option_list_html(page_rows, first_position), unsafe_allow_html=True)
        if page_count > 1:
            st.caption("Page " + str(page_number) + " of " + str(page_count) + ". Numbers are positions in your full list.")

    # Details for one option ------------------------------------------------
    st.divider()
    st.subheader("Look closely at one option")
    option_names = []
    for _, row in ranked.iterrows():
        option_names.append(str(row["list_position"]) + ". " + row["branch"] + ", "
                            + ui.short_institute_name(row["institute"]) + " (" + str(int(row["duration_years"])) + " yrs)")
    chosen_option_name = st.selectbox("Option", option_names, label_visibility="collapsed")
    chosen_row = ranked.iloc[option_names.index(chosen_option_name)]

    detail_columns = st.columns([1, 1], gap="large")
    with detail_columns[0]:
        st.markdown("**Why it scored " + str(int(round(chosen_row["preference_score"]))) + "**")
        contribution_rows = []
        for factor_name in chosen_row["contributions"]:
            contribution_rows.append({"Factor": FACTOR_LABELS[factor_name],
                                      "Points": round(chosen_row["contributions"][factor_name], 1)})
        contribution_table = pd.DataFrame(contribution_rows)
        contribution_chart = alt.Chart(contribution_table).mark_bar(color="#1F6B50", cornerRadiusEnd=3).encode(
            x=alt.X("Points:Q", title="Points out of 100"),
            y=alt.Y("Factor:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            tooltip=["Factor", "Points"],
        ).properties(height=230)
        st.altair_chart(contribution_chart, width="stretch")
        for note_text in chosen_row["notes"]:
            st.markdown(ui.note_html(note_text), unsafe_allow_html=True)

    with detail_columns[1]:
        st.markdown("**Your chance: about " + str(int(round(100 * chosen_row["chance"]))) + "% ("
                    + chosen_row["label"] + ")**")
        history = closing_rank_by_year(closing_ranks, chosen_row["institute"], chosen_row["program"],
                                       chosen_row["seat_type"], chosen_row["gender_pool"])
        history_normal = history[history["closing_is_preparatory"] == False].copy()
        if len(history_normal) > 0:
            history_normal["Year"] = history_normal["year"].astype(str)
            history_normal["Closing rank"] = history_normal["closing_rank"].astype(int)
            line_colour = ui.CHANCE_COLOURS[chosen_row["label"]]
            line = alt.Chart(history_normal).mark_line(
                point=alt.OverlayMarkDef(color=line_colour, size=60), color=line_colour, strokeWidth=2.5,
            ).encode(
                x=alt.X("Year:O", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Closing rank:Q", title="Final-round closing rank", scale=alt.Scale(zero=False)),
                tooltip=["Year", "Closing rank"],
            )
            your_rank = alt.Chart(pd.DataFrame({"Your rank": [int(chosen_row["rank_used"])]})).mark_rule(
                color="#16302A", strokeDash=[5, 4]).encode(y="Your rank:Q", tooltip=["Your rank"])
            st.altair_chart((line + your_rank).properties(height=230), width="stretch")
            st.caption("Seat pool: " + chosen_row["seat_type"] + ", " + chosen_row["gender_pool"]
                       + ". Dashed line: your rank. You get the seat if your rank is at or below the line.")

    facts = []
    if pd.notna(chosen_row.get("nirf_rank")):
        facts.append(("#" + str(int(chosen_row["nirf_rank"])), "NIRF 2025 engineering rank"))
        facts.append((ui.format_rupees(chosen_row["median_salary_inr"]), "median salary of placed graduates (whole IIT)"))
        facts.append((str(int(round(100 * chosen_row["placed_share"]))) + "%", "of 2023-24 graduates placed"))
        facts.append((str(int(round(100 * chosen_row["higher_studies_share"]))) + "%", "went on to higher studies"))
    elif chosen_row["is_abu_dhabi"]:
        facts.append(("No data yet", "Abu Dhabi campus is not ranked separately by NIRF"))
    else:
        facts.append(("Not ranked", "in NIRF 2025 engineering"))
    if pd.notna(chosen_row.get("demand_median_cr")):
        facts.append((ui.format_rank(chosen_row["demand_median_cr"]),
                      "typical OPEN closing rank, " + first_year + "-" + last_year + " (how sought-after)"))
    facts.append((str(chosen_row["city"]), str(chosen_row["region"]) + " region"))
    st.markdown(ui.fact_grid_html(facts), unsafe_allow_html=True)

    st.markdown("**Where graduates of this kind of branch go**")
    group_name = chosen_row["branch_group"]
    if group_name in CORE_PATTERN_NOTES:
        st.write(CORE_PATTERN_NOTES[group_name])
    else:
        st.write("Our research brief has no placement split for this branch group yet.")
    st.caption(CORE_PATTERN_SOURCE + " NIRF salaries are for the whole institute, so they cannot show "
               "how pay differs by branch.")

    # Compare ------------------------------------------------------------------
    st.divider()
    st.subheader("Compare up to three options")
    compare_names = st.multiselect("Pick options to compare", option_names, max_selections=3,
                                   default=option_names[:2])
    if len(compare_names) > 0:
        compare_columns = {}
        for option_name in compare_names:
            option_row = ranked.iloc[option_names.index(option_name)]
            column_values = {}
            column_values["Match score"] = str(int(round(option_row["preference_score"])))
            column_values["Chance"] = option_row["label"] + ", about " + str(int(round(100 * option_row["chance"]))) + "%"
            column_values["Years"] = str(int(option_row["duration_years"]))
            stability_text = option_row["stability_label"]
            if stability_text == "" or pd.isna(stability_text):
                stability_text = "Rarely in your top 10"
            column_values["Stability"] = (stability_text + " (" + str(int(option_row["times_in_top_n"]))
                                          + " of 500 runs in top 10)")
            for factor_name in FACTOR_NAMES:
                factor_score = option_row["factor_scores"][factor_name]
                if factor_score is None:
                    column_values[FACTOR_LABELS[factor_name]] = "not used"
                else:
                    column_values[FACTOR_LABELS[factor_name]] = str(int(round(100 * factor_score))) + " / 100"
            short_name = option_row["branch"] + ", " + ui.short_institute_name(option_row["institute"])
            compare_columns[short_name] = column_values
        compare_table = pd.DataFrame(compare_columns)
        st.dataframe(compare_table, width="stretch", height=36 * (len(compare_table) + 1) + 4)

    # Download -----------------------------------------------------------------
    st.divider()
    st.subheader("Take your list to JoSAA")
    st.caption("Fill choices in this order. Keep several Safe options near the end, so you are sure of a seat. "
               "This is a draft: check every program name and seat type on josaa.nic.in before you submit.")
    choice_list = pd.DataFrame({
        "order": ranked["list_position"],
        "institute": ranked["institute"],
        "program": ranked["program"],
        "chance_label": ranked["label"],
        "chance_percent": (100 * ranked["chance"]).round(0).astype(int),
        "match_score": ranked["preference_score"].round(0).astype(int),
        "stability": ranked["stability_label"].fillna(""),
        "times_in_top10_of_500": ranked["times_in_top_n"].fillna(0).astype(int),
        "flags": ranked["must_have_flags"].apply(ui.join_flags),
    })
    st.download_button("Download my choice list (CSV)", choice_list.to_csv(index=False),
                       file_name="my_josaa_choice_list.csv", mime="text/csv", type="primary")

st.divider()
st.caption(
    "Data: JoSAA final-round opening and closing ranks " + first_year + "-" + last_year
    + " (josaa.nic.in); NIRF 2025 engineering ranking and institute reports (nirfindia.org); IIT fee "
    "remission rules (IIT Mandi and IIT Palakkad official documents). Preparatory-list ranks are left out. "
    "Pilot by the ddr_project team, IIT Delhi. Not an official JoSAA or IIT tool. Starting weights are a "
    "guess until our student survey. Nothing you enter is saved."
)
