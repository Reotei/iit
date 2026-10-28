# IIT Branch Choice Helper (pilot release, v2.3)

v2.3 = v2.2 plus three pre-deployment changes: starting weights are labelled "not a
recommendation" and students are prompted to set their own; a pilot notice says this is not an
official JoSAA or IIT tool and to check choices on josaa.nic.in; and a privacy line says nothing
entered is saved. See `DEPLOY.md` to publish it.

Part of ddr_project, Strategic Intervention to Indian Education. Helps a JEE Advanced
candidate rank IIT branch and institute options by their own priorities, shows the
realistic chance of getting each one, and produces a draft JoSAA choice list.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

The app finds its own `data/` and `static/` folders, so it can be started from any folder. Add `?demo=1` to the address, or press "Try an example student" in the sidebar, to
load a sample student.

## Files

| File | What it does |
|---|---|
| `app.py` | Streamlit interface: sidebar for rank, four step tabs, results |
| `ui.py` | Page styles, the option list and the rank strip |
| `loader.py` | Reads JoSAA closing ranks, drops blank rows, parses "P" ranks, splits program names |
| `feasibility.py` | Seat pools a student can compete in, and the chance of getting each program |
| `scoring.py` | Branch groups, factor scores (0-1), weighted sum with honest handling of missing data |
| `musthaves.py` | Step A: the student's own dealbreakers; removed options keep a plain-language reason |
| `stability.py` | Step B: 500 seeded re-runs with weights changed by up to 20%; Stable / Depends / Fragile labels |
| `test_v22.py` | Tests for must-haves and stability (run `python test_v22.py`) |
| `backtest.py` | Measures how closing ranks move year to year; writes `data/chance_calibration.csv` |
| `validate_chance.py` | Out-of-sample check: calibrate on 2024-25, test on 2026 |
| `data/josaa_iit_final_round_2021_2025.csv` | JoSAA final-round ranks, all IITs, 2021-2025 (josaa.nic.in archive) |
| `data/josaa_iit_final_round_2026.csv` | JoSAA 2026 final round (round 5), incl. IISc (josaa.nic.in) |
| `data/nirf_2025.csv` | NIRF 2025 engineering rank and score; UG 4-year graduates, placed, median salary, higher studies (nirfindia.org institute reports) |
| `data/fees.csv` | IIT tuition and remission rules (IIT Palakkad and IIT Mandi official documents) |
| `data/institutes.csv` | City, state, region of each institute |
| `data/subject_relevance.csv` | How much each branch group uses each school subject. **Team assumption** - validate with faculty |
| `data/chance_calibration.csv` | Output of `backtest.py` |
| `static/fonts/` | Atkinson Hyperlegible and Bricolage Grotesque (SIL Open Font License) |

## How the chance is estimated

For every seat (institute + program + seat type + gender pool) we compare a year's closing
rank with the median of the three years before it. Across thousands of seats this gives the
distribution of year-to-year movement. A student's chance is the share of past cases where
the next closing rank ended up at or above their rank. Seats with a short history and PwD
seats move much more, so they have their own calibration.

Labels come straight from the chance: Safe 90%+, Likely 50-90%, Reach 10-50%, Out below 10%.

**Validation (calibrated on 2024-25, tested on 2026, 2,893 seats):**

| Label | Predicted | Actually got the seat |
|---|---|---|
| Safe | 97.6% | 97.1% |
| Likely | 72.6% | 75.5% |
| Reach | 24.2% | 23.3% |
| Out | 3.5% | 1.5% |

Safe was right 97.3% of the time for seats with full history, 96.4% for new or changed
programs, and 91.9% for PwD seats.

## Pipeline

1. Eligible options: `feasibility.py` gives each program a chance and a label (Safe / Likely / Reach / Out).
   Out is dropped.
2. Must-have filter (`musthaves.py`): removes options that break a rule the student switched on.
3. Score (`scoring.py`): weighted sum, below.
4. Stability check (`stability.py`): how often each option stays in the top 10 when weights shift.
5. Output: sorted by preference score; chance and stability shown next to each option. Chance is
   never used for ordering.

## Must-haves (step 2)

All rules are off unless the student turns them on:

| Rule | Data | If data is missing |
|---|---|---|
| Maximum yearly tuition after remission | `data/fees.csv` | Abu Dhabi fees unknown: kept and flagged "Fees unknown - check before listing" |
| Allowed regions only | `data/institutes.csv` region | - |
| 4-year programs only | Program duration from the JoSAA name | - |
| Never show some branch groups | Branch groups | - |

IIT tuition after remission depends on the student (category, PwD, family income), not the
institute, so the tuition rule keeps all IITs or none of them. A "maximum distance from home" rule
is not possible yet: `institutes.csv` has no coordinates, and none have been invented.

## How the preference score works

Score = sum of (weight x factor score) / sum of weights of factors that were used, x 100.
Coverage shows the share of the weights actually scored.

| Factor | Data | Status |
|---|---|---|
| Interest | Student (required) | Used |
| Fit with strengths | Student's subject ratings x `subject_relevance.csv` | Used (assumption) |
| Salary | NIRF 2025 median salary, whole institute, 3-batch average | Used |
| Institute ranking | NIRF 2025 engineering score, rescaled across IITs | Used |
| How sought-after it is | Median OPEN gender-neutral closing rank 2024-26, log scale, rescaled 0-1 across IIT programs | Used, default "A little" |
| Location | Institute region | Used |
| Fees and early earning | Tuition after remission vs budget; 4 vs 5 years | Used |
| Family's view | Student | Used |
| Career path, flexibility, campus life | Survey and institute rules | Not yet |

Rules that protect fairness:
- Results are sorted by preference, never by chance. Exact ties are broken by how sought-after the program is.
- "How sought-after" shows what other students chose, not what suits this student, so its default weight
  is low. It is kept separate from "institute ranking" (NIRF), which measures something different.
- The IIT Delhi Abu Dhabi campus does not borrow IIT Delhi's NIRF ranking or salary; it is scored neutral
  until it has data of its own.
- A factor is used for every option or for none. If one institute lacks data (IIT Goa and
  IISc are not in NIRF engineering; Abu Dhabi fees are unknown), it gets a neutral 0.5 and
  a visible note.
- Interest is required. Options in a group the student did not rate are set aside, and the
  interest weight cannot be set to "Ignore".
- Must-haves: no default dealbreakers; the tool never removes options on the student's behalf.
  Removed options are listed with every reason in "Removed by your must-haves (N)", never
  silently dropped. Must-haves run after feasibility and before scoring.

## Stability check (step 4)

Factor scores are computed once. In each of 500 runs every weight is multiplied by a random number
between 0.8 and 1.2 (a weight of 0 stays 0), options are re-scored with the same formula and the
same tie-break, and the top 10 is recorded. Random seed 42, so the same inputs always give the same
labels.

| Share of runs in the top 10 | Label |
|---|---|
| 80% or more | Stable pick |
| 40-80% | Depends on your weights |
| Below 40% | Fragile (only shown if the option was ever in the top 10) |

Tests: equal factor scores follow the tie-break rule; with no weight change every base top-10
option is Stable pick; the same seed gives identical output. 351 options x 500 runs takes about
0.05 seconds.

## Worked check: AIR 1

IIT Bombay CSE had the best OPEN closing rank in 2026 (67, vs 128 Delhi and 151 Madras). For an AIR 1
student who loves computing, with default weights the tool ranks Madras CSE 1st and Bombay CSE 2nd
(97.9 vs 96.4), because NIRF 2025 ranks Madras first. With "How sought-after" raised to "Some" (equal to
institute ranking), Bombay CSE ranks 1st. An AIR 1 student who loves mechanical engineering gets
mechanical programs first and Bombay CSE 33rd: a top rank does not push anyone into CSE.

Stability (v2.2), same student, default weights: Madras CSE, Bombay CSE and Delhi CSE are all
"Stable pick" (in the top 10 in 500 of 500 runs). Madras CSE stays 1st in all 500 runs, so a
+-20% change in weights does not overturn NIRF's lead; only a deliberate change (for example
"How sought-after" set to "Some") does. 10th place (IIT Kharagpur CSE) is "Depends on your
weights" (350 of 500 runs).

## Known limitations

- NIRF salaries are institute-wide, not by branch, so they cannot show core vs non-core pay.
- Core vs non-core notes come from one IIT Bombay study (research brief section 2.3).
- `subject_relevance.csv` and the 5-year penalty (0.4) are team assumptions.
- Default weights are placeholders until the student survey (question 31) sets them.
- Hostel, mess and scholarships are not in the fee calculation.
- "Computing" groups CSE, AI, data science and maths-and-computing together; students cannot yet rate
  sub-branches separately.
- Preparatory-list closing ranks are left out of chance estimates.
- Stability uses +-20% uniform changes to every weight at once: a team assumption, not measured.
  The label is about staying in the top 10, not about the exact order within it.
