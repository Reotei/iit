"""
ui.py — look and feel for the Streamlit app: page styles, the option list with
rank strips, and small HTML pieces. Kept separate from app.py so the app file
reads as the flow of the page.
"""

import html


CHANCE_COLOURS = {
    "Safe": "#2E7D5B",
    "Likely": "#B8901C",
    "Reach": "#9C3D68",
    "Out": "#8A948F",
}

STABILITY_COLOURS = {
    "Stable pick": "#1F6B50",
    "Depends on your weights": "#9A7414",
    "Fragile": "#8A3A5E",
}


def join_flags(flag_list):
    """["a", "b"] -> "a; b" (for the CSV download)."""
    if not isinstance(flag_list, list):
        return ""
    return "; ".join(flag_list)


PAGE_STYLE = """
<style>
/* Fonts come from .streamlit/config.toml (bundled in static/fonts). */
h1, h2, h3, h4 { letter-spacing: -0.01em; color: #16302A; }
h1 { font-weight: 700 !important; font-size: 2.15rem !important; line-height: 1.1 !important; }
h2 { font-weight: 700 !important; }
h3 { font-weight: 600 !important; }

.block-container { padding-top: 2rem; max-width: 1100px; }

.hero-text { font-size: 1.08rem; line-height: 1.55; max-width: 62ch; color: #2B4A42; margin-bottom: 0.3rem; }

.step-hint { color: #4D6660; font-size: 0.95rem; margin: -0.3rem 0 1rem 0; max-width: 70ch; }

.group-title { font-weight: 700; font-size: 1rem; color: #16302A; margin-top: 0.6rem; }
.group-blurb { color: #5A716B; font-size: 0.88rem; line-height: 1.35; margin: 0.05rem 0 0 0 !important; padding-bottom: 1.3rem !important; }

/* Summary chips */
.chance-summary { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.2rem 0 1rem 0; }
.chance-chip { border-radius: 999px; padding: 0.3rem 0.85rem; font-size: 0.95rem; color: #fff; }
.chance-chip b { font-weight: 700; }

/* Option list */
.option-list { list-style: none; padding: 0; margin: 0; counter-reset: none; }
.option-row {
  display: grid;
  grid-template-columns: 2.6rem minmax(0, 1fr) 12.5rem;
  gap: 0.9rem;
  align-items: center;
  padding: 0.9rem 0.2rem 1.25rem 0.2rem;
  border-bottom: 1px solid #D3DED6;
}
.option-order {
  font-family: 'Bricolage Grotesque', sans-serif;
  font-size: 1.5rem; font-weight: 700; color: #1F6B50; text-align: right;
}
.option-branch { font-weight: 700; font-size: 1.04rem; color: #16302A; line-height: 1.25; }
.option-institute { color: #4D6660; font-size: 0.92rem; margin-top: 0.1rem; }
.option-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.4rem; align-items: center; }
.badge {
  display: inline-block; border-radius: 4px; padding: 0.08rem 0.5rem;
  font-size: 0.8rem; font-weight: 700; color: #fff;
}
.soft-tag { display: inline-block; font-size: 0.8rem; color: #4D6660; background: #E4EBE5; border-radius: 4px; padding: 0.08rem 0.45rem; }
.stability-tag { display: inline-block; font-size: 0.8rem; font-weight: 700; border-radius: 4px; padding: 0.02rem 0.45rem; border: 1.5px solid; background: transparent; }
.flag-tag { display: inline-block; font-size: 0.8rem; color: #7A4B00; background: #FBEFD5; border-radius: 4px; padding: 0.08rem 0.45rem; }
.score-block { text-align: right; }
.score-number { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.35rem; font-weight: 700; color: #16302A; }
.score-label { font-size: 0.78rem; color: #5A716B; }

/* Rank strip: the signature element */
.rank-strip { position: relative; height: 44px; margin-top: 0.55rem; max-width: 520px; }
.rank-strip .axis { position: absolute; left: 0; right: 0; top: 14px; height: 2px; background: #C9D6CD; }
.rank-strip .band { position: absolute; top: 9px; height: 12px; border-radius: 3px; opacity: 0.28; }
.rank-strip .median { position: absolute; top: 6px; width: 2px; height: 18px; }
.rank-strip .you { position: absolute; top: 7px; width: 16px; height: 16px; margin-left: -8px; border-radius: 50%;
  background: #16302A; border: 3px solid #F2F5F1; box-shadow: 0 0 0 1.5px #16302A; }
.rank-strip .you-label { position: absolute; top: 24px; font-size: 0.72rem; color: #16302A; transform: translateX(-50%); white-space: nowrap; font-weight: 700; }
.rank-strip .end-label { position: absolute; top: 24px; font-size: 0.7rem; color: #6D817B; white-space: nowrap; }

.fact-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.6rem 1.2rem; margin: 0.4rem 0 0.8rem 0; }
.fact-value { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.25rem; font-weight: 700; color: #16302A; }
.fact-label { font-size: 0.82rem; color: #5A716B; }

.pilot-notice { border: 1.5px solid #B8901C; background: #FBF4E2; color: #4A3A10; border-radius: 4px;
  padding: 0.65rem 0.9rem; font-size: 0.92rem; line-height: 1.5; max-width: 80ch; margin: 0.2rem 0 1rem 0; }
.pilot-notice a { color: #1F6B50; font-weight: 700; }
.note-box { border-left: 3px solid #1F6B50; background: #E9F0EB; padding: 0.6rem 0.9rem; border-radius: 0 4px 4px 0; font-size: 0.93rem; color: #2B4A42; margin: 0.4rem 0; }

@media (max-width: 640px) {
  h1 { font-size: 1.8rem !important; }
  .option-row { grid-template-columns: 2rem minmax(0, 1fr); }
  .score-block { grid-column: 2; text-align: left; }
}
</style>
"""


def format_rank(rank_value):
    """12345 -> '12,345' (simple thousands separator, as JoSAA prints ranks)."""
    return "{:,}".format(int(round(rank_value)))


def format_rupees(amount):
    """Indian lakh format for salaries/fees: 1750000 -> 'Rs 17.5 lakh'."""
    lakhs = amount / 100000
    if lakhs >= 1:
        return "Rs " + ("%.1f" % lakhs).rstrip("0").rstrip(".") + " lakh"
    return "Rs " + "{:,}".format(int(round(amount)))


def short_institute_name(full_name):
    shorter = full_name.replace("Indian Institute of Technology", "IIT")
    shorter = shorter.replace("Indian Institute of Science, Bangalore", "IISc Bangalore")
    return shorter


def chance_summary_html(label_counts):
    parts = ['<div class="chance-summary">']
    for label_name in ["Safe", "Likely", "Reach"]:
        count_value = int(label_counts.get(label_name, 0))
        parts.append('<span class="chance-chip" style="background:' + CHANCE_COLOURS[label_name] + '">'
                     + '<b>' + str(count_value) + '</b> ' + label_name + '</span>')
    parts.append('</div>')
    return "".join(parts)


def rank_strip_html(student_rank, lowest_cr, median_cr, highest_cr, label_name):
    """
    A horizontal ruler. Left = better (smaller) rank.
    The shaded band covers past closing ranks (lowest to highest), the tick is the
    median, and the dark dot is the student's rank.
    """
    left_end = min(student_rank, lowest_cr) * 0.85
    right_end = max(student_rank, highest_cr) * 1.12
    span = right_end - left_end
    if span <= 0:
        span = 1

    def position_percent(rank_value):
        return 100 * (rank_value - left_end) / span

    band_left = position_percent(lowest_cr)
    band_width = max(1.5, position_percent(highest_cr) - band_left)
    median_left = position_percent(median_cr)
    you_left = position_percent(student_rank)
    colour = CHANCE_COLOURS[label_name]

    # Keep the "You" label inside the strip
    label_left = min(max(you_left, 6), 94)

    return (
        '<div class="rank-strip" role="img" aria-label="Your rank ' + format_rank(student_rank)
        + ' against past closing ranks ' + format_rank(lowest_cr) + ' to ' + format_rank(highest_cr) + '">'
        + '<div class="axis"></div>'
        + '<div class="band" style="left:' + str(round(band_left, 2)) + '%;width:' + str(round(band_width, 2))
        + '%;background:' + colour + '"></div>'
        + '<div class="median" style="left:' + str(round(median_left, 2)) + '%;background:' + colour + '"></div>'
        + '<div class="you" style="left:' + str(round(you_left, 2)) + '%"></div>'
        + '<div class="you-label" style="left:' + str(round(label_left, 2)) + '%">You ' + format_rank(student_rank) + '</div>'
        + '</div>'
    )


def option_row_html(order_number, row):
    label_name = row["label"]
    colour = CHANCE_COLOURS[label_name]
    chance_percent = int(round(100 * row["chance"]))

    tags = []
    tags.append('<span class="badge" style="background:' + colour + '">' + label_name
                + ', about ' + str(chance_percent) + '% chance</span>')
    tags.append('<span class="soft-tag">' + str(int(row["duration_years"])) + ' years</span>')
    if row["lowest_cr"] == row["highest_cr"]:
        range_text = "closed at " + format_rank(row["lowest_cr"])
    else:
        range_text = "closed between " + format_rank(row["lowest_cr"]) + " and " + format_rank(row["highest_cr"])
    tags.append('<span class="soft-tag">' + range_text + '</span>')
    if row["seat_type"] != "OPEN" or row["gender_pool"] != "Gender-Neutral":
        pool_text = row["seat_type"]
        if row["gender_pool"] != "Gender-Neutral":
            pool_text = pool_text + ", female-only seat"
        tags.append('<span class="soft-tag">via ' + html.escape(pool_text) + '</span>')
    if row["low_confidence"]:
        tags.append('<span class="soft-tag">new or changed program</span>')

    stability_label = row.get("stability_label", "")
    if isinstance(stability_label, str) and stability_label != "":
        stability_colour = STABILITY_COLOURS[stability_label]
        tags.append('<span class="stability-tag" style="color:' + stability_colour + ';border-color:'
                    + stability_colour + '" title="In your top 10 in ' + str(int(row["times_in_top_n"]))
                    + ' of 500 re-runs">' + stability_label + '</span>')

    flags = row.get("must_have_flags", [])
    if isinstance(flags, list):
        for flag_text in flags:
            tags.append('<span class="flag-tag">' + html.escape(flag_text) + '</span>')

    return (
        '<li class="option-row">'
        + '<div class="option-order">' + str(order_number) + '</div>'
        + '<div>'
        + '<div class="option-branch">' + html.escape(row["branch"]) + '</div>'
        + '<div class="option-institute">' + html.escape(short_institute_name(row["institute"]))
        + ', ' + html.escape(str(row["city"])) + '</div>'
        + '<div class="option-meta">' + "".join(tags) + '</div>'
        + rank_strip_html(row["rank_used"], row["lowest_cr"], row["median_cr"], row["highest_cr"], label_name)
        + '</div>'
        + '<div class="score-block"><div class="score-number">' + str(int(round(row["preference_score"])))
        + '<span class="score-label"> / 100</span></div><div class="score-label">fit with your priorities</div></div>'
        + '</li>'
    )


def option_list_html(rows_table, start_number):
    parts = ['<ol class="option-list">']
    order_number = start_number
    for _, row in rows_table.iterrows():
        parts.append(option_row_html(order_number, row))
        order_number = order_number + 1
    parts.append('</ol>')
    return "".join(parts)


def fact_grid_html(facts):
    """facts: list of (value_text, label_text)."""
    parts = ['<div class="fact-grid">']
    for value_text, label_text in facts:
        parts.append('<div><div class="fact-value">' + html.escape(value_text) + '</div>'
                     + '<div class="fact-label">' + html.escape(label_text) + '</div></div>')
    parts.append('</div>')
    return "".join(parts)


def note_html(text):
    return '<div class="note-box">' + html.escape(text) + '</div>'
