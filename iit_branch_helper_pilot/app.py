"""
app.py — entry point for the IIT Branch Choice Helper.

Run with:   streamlit run app.py

This file only sets up the shared page (title, styles) and the menu of pages.
Each page lives in its own file:
  branch_choice.py   -> the branch-choice tool (built and validated)
  drift_page.py      -> drift early-warning check (proposed design, demo)
  matching_page.py   -> core internship matching (proposed design, demo with made-up data)
"""

import os

import streamlit as st

# The data files are read by relative path ("data/...", "static/..."). Hosting services
# do not always start the app from this folder, so move into it before loading anything.
APP_FOLDER = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_FOLDER)

import ui

st.set_page_config(page_title="IIT Branch Choice Helper", page_icon="🎓", layout="wide")
st.markdown(ui.PAGE_STYLE, unsafe_allow_html=True)

# Full paths, so every Streamlit version finds the page files wherever the app is started from
branch_choice_page = st.Page(os.path.join(APP_FOLDER, "branch_choice.py"), title="Branch choice",
                             url_path="branch_choice", default=True)
drift_page = st.Page(os.path.join(APP_FOLDER, "drift_page.py"), title="Drift check (proposed)",
                     url_path="drift_page")
matching_page = st.Page(os.path.join(APP_FOLDER, "matching_page.py"), title="Internship matching (proposed)",
                        url_path="matching_page")

page_menu = {
    "Before you join": [branch_choice_page],
    "After you join (proposed)": [drift_page, matching_page],
}
chosen_page = st.navigation(page_menu, position="sidebar")
chosen_page.run()
