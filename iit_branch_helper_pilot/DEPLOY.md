# Deploying the pilot

This folder is ready to deploy as it is. `app.py` is the main file; everything it needs
(data, fonts, theme) is inside this folder.

## Option 1: Streamlit Community Cloud (free, simplest)

1. Create a GitHub repository and upload the **contents** of this folder to it, so that
   `app.py`, `requirements.txt`, `data/`, `static/` and `.streamlit/` sit at the top level.
   `.streamlit/` is a hidden folder: make sure it is uploaded too, or the colours and fonts
   will be missing.
2. Sign in at share.streamlit.io with your GitHub account and choose "Create app".
3. Pick the repository and branch, and set the main file to `app.py`.
4. Under advanced settings, choose Python 3.11 or newer (tested on 3.13).
5. Deploy. The first start takes a few minutes while it installs the packages.

## Option 2: Hugging Face Spaces

Create a new Space with the Streamlit option, upload the same files, and set the app file to
`app.py`. Check the Space's settings for the Python version.

## Before you share the link

- Open the app, press "Try an example student", and check the choice list appears.
- Run the tests locally: `python test_v22.py` (all should print PASS).
- Share the link with the pilot group only, with the note that it is a pilot.

## What the app does and does not do with student data

The app does not save, log or send anywhere what a student enters. Inputs exist only in that
browser session while the page is open. If you later add a feedback form or usage logging, check
with your course instructor about consent first, and update the notice at the top of the app.

## Every year (before JoSAA counselling)

The chances depend on the latest closing ranks. Before each counselling season:

1. Download the previous year's final-round IIT opening and closing ranks from the JoSAA archive
   (all IITs, all seat types, all genders) into a CSV with the same columns as
   `data/josaa_iit_final_round_2026.csv`.
2. Add the file to `CLOSING_RANK_FILES` in `loader.py`, and move `YEARS_TO_USE` in
   `feasibility.py` and `DEMAND_YEARS` in `scoring.py` forward by one year.
3. Run `python backtest.py` to refresh `data/chance_calibration.csv`, then
   `python validate_chance.py` to check the chances still hold up.
4. Update `data/nirf_*.csv` when a new NIRF ranking is published.
