"""
loader.py — Segment 1: read the JoSAA closing-rank CSV and clean it.

What this segment does, step by step:
  1. Read the CSV with every column as text (so nothing is silently converted).
  2. Drop blank rows (the empty footer row JoSAA adds to every year's table).
  3. Turn year and round into whole numbers.
  4. Turn opening and closing ranks into numbers, and record separately
     whether a rank came from the Preparatory Rank List (suffix "P").
  5. Split the program name into branch name, duration in years and degree.
"""

import re
import pandas as pd


# ---------------------------------------------------------------------------
# Step 1: read the raw file
# ---------------------------------------------------------------------------
def read_raw_csv(file_path):
    """Read the CSV exactly as text. dtype=str stops pandas guessing types."""
    raw_table = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    return raw_table


# ---------------------------------------------------------------------------
# Step 2: drop blank rows
# ---------------------------------------------------------------------------
def drop_blank_rows(table):
    """A row is blank if its institute name is empty."""
    institute_is_filled = table["institute"].str.strip() != ""
    cleaned_table = table[institute_is_filled].copy()
    return cleaned_table


# ---------------------------------------------------------------------------
# Step 4 helper: parse one rank value such as "12396" or "245P"
# ---------------------------------------------------------------------------
def parse_rank(rank_text):
    """
    Returns a pair: (rank_number, is_preparatory)
      "12396" -> (12396, False)
      "245P"  -> (245, True)
      ""      -> (None, False)   # missing rank
    """
    cleaned_text = rank_text.strip()

    if cleaned_text == "":
        return (None, False)

    is_preparatory = False
    if cleaned_text.endswith("P"):
        is_preparatory = True
        cleaned_text = cleaned_text[:-1]  # remove the trailing "P"

    rank_number = int(float(cleaned_text))  # float() first handles "123.0" safely
    return (rank_number, is_preparatory)


# ---------------------------------------------------------------------------
# Step 5 helper: split a program name
# "Civil Engineering (4 Years, Bachelor of Technology)"
#   -> ("Civil Engineering", 4, "Bachelor of Technology")
# ---------------------------------------------------------------------------
PROGRAM_PATTERN = re.compile(r"^(.*?) \((\d+) Years?, (.*)\)$")


def split_program_name(program_text):
    match_result = PROGRAM_PATTERN.match(program_text.strip())

    if match_result is None:
        # Unknown format: keep the full text as the branch name, flag the rest as missing
        return (program_text.strip(), None, None)

    branch_name = match_result.group(1).strip()
    duration_years = int(match_result.group(2))
    degree_name = match_result.group(3).strip()
    return (branch_name, duration_years, degree_name)


# ---------------------------------------------------------------------------
# Main function: run all steps in order
# ---------------------------------------------------------------------------
def load_closing_ranks(file_path):
    table = read_raw_csv(file_path)
    table = drop_blank_rows(table)

    # Step 3: year and round as whole numbers
    table["year"] = table["year"].astype(int)
    table["round"] = table["round"].astype(int)

    # Step 4: ranks
    opening_numbers = []
    opening_is_prep = []
    closing_numbers = []
    closing_is_prep = []

    for opening_text, closing_text in zip(table["opening_rank"], table["closing_rank"]):
        opening_number, opening_prep_flag = parse_rank(opening_text)
        closing_number, closing_prep_flag = parse_rank(closing_text)
        opening_numbers.append(opening_number)
        opening_is_prep.append(opening_prep_flag)
        closing_numbers.append(closing_number)
        closing_is_prep.append(closing_prep_flag)

    table["opening_rank"] = pd.array(opening_numbers, dtype="Int64")
    table["closing_rank"] = pd.array(closing_numbers, dtype="Int64")
    table["opening_is_preparatory"] = opening_is_prep
    table["closing_is_preparatory"] = closing_is_prep

    # Step 5: program name pieces
    branch_names = []
    durations = []
    degrees = []
    for program_text in table["program"]:
        branch_name, duration_years, degree_name = split_program_name(program_text)
        branch_names.append(branch_name)
        durations.append(duration_years)
        degrees.append(degree_name)

    table["branch"] = branch_names
    table["duration_years"] = pd.array(durations, dtype="Int64")
    table["degree"] = degrees

    table = table.reset_index(drop=True)
    return table


# ---------------------------------------------------------------------------
# All years together
# ---------------------------------------------------------------------------
CLOSING_RANK_FILES = [
    "data/josaa_iit_final_round_2021_2025.csv",
    "data/josaa_iit_final_round_2026.csv",
]


def load_all_closing_ranks(file_paths=None):
    if file_paths is None:
        file_paths = CLOSING_RANK_FILES
    tables = []
    for file_path in file_paths:
        tables.append(load_closing_ranks(file_path))
    combined_table = pd.concat(tables, ignore_index=True)
    return combined_table
