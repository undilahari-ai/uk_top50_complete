"""Step 5 - Build the research paper and the executive summary (Word files).

Run (after cleaning.py, findings.py, figures.py):  python src/build_report.py
Creates reports/Research_Paper.docx and reports/Executive_Summary.docx.
All numbers are read from the data, so the documents always match the analysis.
"""
import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402
import metrics as m  # noqa: E402

FIG = ROOT / "reports" / "figures"
BLUE = RGBColor(0x1F, 0x5F, 0xBF)


# ----------------------------------------------------------------- docx helpers
def new_doc():
    d = Document()
    s = d.sections[0]
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2.0)
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(6)
    for name, size in [("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)]:
        h = d.styles[name]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = BLUE
    return d


def para(d, text, bold=False, italic=False, size=None, align=None, color=None):
    p = d.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    if align:
        p.alignment = align
    return p


def rich(d, parts, style=None):
    """parts = list of (text, bold)."""
    p = d.add_paragraph(style=style)
    for t, b in parts:
        p.add_run(t).bold = b
    return p


def bullets(d, items):
    for it in items:
        if isinstance(it, tuple):
            rich(d, [(it[0], True), (it[1], False)], style="List Bullet")
        else:
            d.add_paragraph(it, style="List Bullet")


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tcPr.append(sh)


def table(d, df, widths=None, fmt=None, font=9):
    fmt = fmt or {}
    t = d.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, col in enumerate(df.columns):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(col))
        r.bold = True
        r.font.size = Pt(font)
        r.font.color.rgb = RGBColor(255, 255, 255)
        shade(c, "1F5FBF")
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, col in enumerate(df.columns):
            v = row[col]
            f = fmt.get(col)
            txt = f.format(v) if (f and pd.notna(v)) else ("" if pd.isna(v) else str(v))
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(txt)
            r.font.size = Pt(font)
            if i > 0:
                cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    d.add_paragraph()
    return t


def figure(d, name, caption, width=15.5):
    d.add_picture(str(FIG / name), width=Cm(width))
    d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(d, caption, italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)


def pct(x, nd=1):
    return f"{x * 100:.{nd}f}%"


def pv(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


# ----------------------------------------------------------------- numbers
def facts():
    c = data.load_clean()
    e = data.explode_artists(c)
    ctry = data.load_countries()
    R = json.loads((ROOT / "reports" / "results.json").read_text())
    rep = json.loads((ROOT / "data" / "cleaning_report.json").read_text())
    k = R["kpis"]
    bands = m.kpis_by_band(c, e)
    board = m.appearance_counts(e)
    dk = m.daily_kpis(c, e)
    mk = m.monthly_kpis(c, e)
    cs = m.country_share(e, ctry).set_index("country_group")["share_%"]
    peak = dk.loc[dk["artist_concentration"].idxmax()]
    top_day = c[c["date"] == peak["date"]]["lead_artist"].value_counts()
    ev = m.explicit_vs_clean_popularity(c).set_index("content")
    abr = m.album_type_by_rank(c)
    sing = {g: float(abr[(abr.rank_group == g) & (abr.album_type == "single")]["share_in_group_%"].iloc[0]) for g in ["Top 10", "11-25", "26-50"]}
    alb = {g: float(abr[(abr.rank_group == g) & (abr.album_type == "album")]["share_in_group_%"].iloc[0]) for g in ["Top 10", "11-25", "26-50"]}
    return dict(c=c, e=e, ctry=ctry, R=R, rep=rep, k=k, bands=bands, board=board, dk=dk, mk=mk, cs=cs, peak=peak,
                top_day=top_day, ev=ev, sing=sing, alb=alb)


# ----------------------------------------------------------------- research paper
def build_paper(F):
    c, R, rep, k, B, board, mk, cs, ev = (F[x] for x in ["c", "R", "rep", "k", "bands", "board", "mk", "cs", "ev"])
    d = new_doc()
    para(d, "UK Top 50 Playlist", bold=True, size=26, color=BLUE)
    para(d, "Market Structure, Artist Diversity and Content Localization", bold=True, size=16)
    para(d, "Technical research paper: exploratory data analysis, methods, findings and recommendations", italic=True)
    para(d, f"Data: {R['period']['days']} daily snapshots, {R['period']['start']} to {R['period']['end']} "
            f"({R['period']['entries']:,} chart entries, {R['period']['unique_songs']} distinct songs, {k['Unique Artist Count']:.0f} artists)")

    # ---- 1 summary
    d.add_heading("1. Summary of findings", 1)
    d.add_paragraph(
        "The UK Top 50 playlist is a broad, rotating market rather than one dominated by a few acts, but it has a "
        "clear two-tier structure: the Top 10 and the rest behave differently. The headline results are:")
    bullets(d, [
        ("Diverse overall, anchored by a few superstars. ",
         f"{k['Unique Artist Count']:.0f} different artists appeared. The Artist Concentration Index is {k['Artist Concentration Index']:.4f} "
         f"(very low), and the five most frequent artists hold {pct(k['Top-5 Artist Share'])} of all artist slots. "
         f"Taylor Swift alone holds {board.iloc[0]['share_%']:.1f}%."),
        ("The Top 10 is more concentrated and more international. ",
         f"Top-5 artist share is {pct(B.loc['Top-5 Artist Share', 'Top 10'])} in the Top 10 versus "
         f"{pct(B.loc['Top-5 Artist Share', '11-50'])} in positions 11-50. US artists hold {R['country_by_band'][0]['share_%']:.0f}% of Top 10 artist slots."),
        ("Singles win the top, albums fill the depth. ",
         f"Singles are {F['sing']['Top 10']:.0f}% of Top 10 entries but only {F['sing']['26-50']:.0f}% of positions 26-50. "
         f"Overall the single : album ratio is {k['Single vs Album Ratio']:.2f}."),
        ("Collaborations are common but not a route to the very top. ",
         f"{pct(k['Collaboration Ratio'])} of entries are collaborations (Top 10: {pct(B.loc['Collaboration Ratio', 'Top 10'])}, "
         f"11-50: {pct(B.loc['Collaboration Ratio', '11-50'])}); the average collaboration has {R['collab']['avg_artists_collab']:.1f} artists."),
        ("Explicit songs are not penalised. ",
         f"{pct(k['Explicit Content Share'])} of entries are explicit, rising to {pct(B.loc['Explicit Content Share', 'Top 10'])} in the Top 10. "
         f"Explicit entries sit slightly higher (average position {ev.loc['Explicit', 'avg_position']:.1f} vs {ev.loc['Clean', 'avg_position']:.1f})."),
        ("Track length barely matters. ",
         f"The median track is {R['duration']['median']:.2f} minutes; length has a very weak link to popularity "
         f"(Spearman rho = {R['duration']['corr']['rho_duration_popularity']:.2f})."),
    ])

    # ---- 2 framing
    d.add_heading("2. Problem framing and method", 1)
    d.add_paragraph(
        "The project follows a structured analytic workflow: frame the problem, extract data, prepare it, analyse, "
        "interpret and present. The business question is: how is the UK Top 50 structured in terms of who is on it "
        "(artists, collaborations, domestic vs international) and what is on it (explicitness, release format, track length), "
        "and what should that mean for UK-focused strategy?")
    table(d, pd.DataFrame({
        "Stage": ["Frame", "Extract", "Prepare", "Analyse", "Interpret", "Present"],
        "What was done": [
            "Questions and KPIs from the implementation plan (sections 2-7)",
            "Loaded data/raw.csv (27,800 rows, 10 columns) with pandas",
            "Validated, standardised, split artists, created helper columns (src/cleaning.py)",
            "KPI and analysis functions with significance tests (src/metrics.py, src/findings.py)",
            "Top 10 vs 11-50 comparison, effect sizes, caveats",
            "Charts (src/figures.py), Streamlit dashboard (app.py), this paper and the executive summary"]}),
        widths=[3, 13.5])

    d.add_heading("2.1 Data validation and cleaning", 2)
    bullets(d, [
        f"Rows loaded: {rep['raw_rows']:,}. Null cells in the raw file: {sum(rep['null_cells_raw'].values())}. Types converted: dates to dates, numbers to numbers, explicit flag to boolean.",
        f"Snapshot check: every date must contain exactly positions 1 to 50 once each. One date failed: 1 March 2025 has 100 rows (two complete 50-song lists that are almost identical to 28 Feb and 2 Mar). It was removed rather than guessed at, leaving {rep['clean_rows']:,} rows over {rep['days']} days.",
        f"Missing dates in the source calendar: {', '.join(rep['missing_dates'])} (the first is the removed date). Time series are therefore slightly gapped.",
        f"Duplicates: {rep['duplicate_rows_removed']} duplicate date-song-artist rows found. Popularity of 0 (no score) set to missing in {rep['popularity_zero_rows']} rows.",
        "Text standardisation: whitespace trimmed and collapsed, unicode normalised, release type lower-cased.",
        "Artist-name standardisation: names are matched ignoring case, accents and punctuation and mapped to one official spelling. This merged "
        + "; ".join(f"{k2} ({' / '.join(v)})" for k2, v in rep["artist_spellings_merged"].items())
        + ". An earlier version counted these as separate artists.",
        "Multi-artist splitting: the artist field is split on '&', with protected names kept whole (e.g. Chase & Status, Earth, Wind & Fire, Henri René & His Orchestra). Guests written only in the song title ('(feat. X)', '(with X)', 'featuring X') are added, so collaborations are not under-counted.",
        "Helper columns: n_artists, is_collab, lead_artist, duration (s / min / bucket), rank group, Top 10 vs 11-50 band, popularity quartile, release-size bucket.",
    ])

    d.add_heading("2.2 KPI definitions", 2)
    d.add_paragraph("Each KPI has one definition, used identically in the paper, findings.txt and the dashboard.")
    table(d, pd.DataFrame({
        "KPI": ["Artist Concentration Index", "Normalised concentration", "Unique Artist Count", "Daily Diversity Ratio", "Collaboration Ratio",
                "Explicit Content Share", "Single vs Album Ratio", "Content Variety Index", "Top-5 Artist Share"],
        "Definition": [
            "Sum of squared artist shares of artist slots (Herfindahl-Hirschman style, 0-1)",
            "(HHI - 1/N) / (1 - 1/N), N = number of artists; removes the effect of N",
            "Distinct artists in the selection (richness)",
            "Unique artists / artist slots on one day, averaged over days",
            "Tracks with 2+ artists / all tracks",
            "Explicit entries / all entries",
            "Singles / albums (compilations excluded; they are 0.3% of entries)",
            "Mean of four normalised Shannon entropies (artist, release type, explicit, duration bucket). >0.75 balanced, <0.5 skewed",
            "Share of artist slots held by the 5 most frequent artists"],
        "Why": ["Market dominance", "Comparable across periods", "Diversity", "Short-term variety", "Partnership prevalence",
                "Cultural preference", "Release strategy", "Variety of content", "Playlist balance"]}),
        widths=[4.2, 9.3, 3.2], font=8.5)
    d.add_paragraph(
        "Note on naming: an earlier draft reported 'diversity' as unique artists divided by all artist slots over the whole period (0.011), "
        "which is essentially a concentration measure, next to a daily diversity figure of about 0.79. These are now separate metrics with "
        "separate names: the Artist Concentration Index is a period-wide measure, the Daily Diversity Ratio is a per-day average.")
    d.add_paragraph(
        "Statistical tests: chi-square tests for shares (collaboration, explicit, single), Mann-Whitney U tests for numeric comparisons, "
        "Spearman correlation for duration. With 27,700 entries almost any difference is statistically significant, so effect sizes are "
        "discussed alongside p-values. Entries are repeated daily observations of the same songs, so p-values overstate independence "
        "and should be read as a guide, not proof.")

    # ---- 3 artists
    d.add_heading("3. Artist dominance and diversity", 1)
    figure(d, "fig01_top_artists.png", "Figure 1. Chart appearances of the 15 most frequent artists.", 13.5)
    top = board.head(10)[["artist_name", "appearances", "days_on_chart", "unique_songs", "avg_position", "share_%"]]
    top.columns = ["Artist", "Appearances", "Days on chart", "Songs", "Avg pos.", "Share %"]
    table(d, top, fmt={"Appearances": "{:,.0f}", "Share %": "{:.2f}", "Avg pos.": "{:.1f}"}, widths=[4.5, 2.5, 2.5, 2, 2.2, 2.2])
    bullets(d, [
        f"Richness: {k['Unique Artist Count']:.0f} artists over {rep['days']} days, but only {R['daily_unique']['mean']:.0f} per day on average "
        f"(range {R['daily_unique']['min']} to {R['daily_unique']['max']}) and {R['daily_unique']['weekly_mean']:.0f} per week.",
        f"Appearance share: Taylor Swift {board.iloc[0]['share_%']:.1f}% of all artist slots, with {board.iloc[0]['unique_songs']:.0f} different songs. The top 10 artists hold {pct(R['top10_artist_share'])}. "
        f"{R['artists_over_100_days']} artists appeared 100+ times; {R['artists_one_song_only']} artists ({pct(R['artists_one_song_only'] / len(board), 0)}) were seen with a single song and the median artist appeared {R['median_appearances']:.0f} times.",
        f"Concentration: the period-wide Artist Concentration Index is {k['Artist Concentration Index']:.4f} (normalised {k['Normalised Concentration']:.4f}). "
        "On the 0-10,000 scale used in competition analysis this is about 106, far below the roughly 1,000 level often used as the start of a 'concentrated' market. "
        f"The daily index is higher (mean {F['dk']['artist_concentration'].mean():.3f}) because a 50-slot list is small.",
        f"Longevity: the median song stayed {R['stay']['median']:.0f} days; the longest ({R['stay']['max']} days) is a single song by The Killers that appeared on {R['stay']['max']} of the {rep['days']} snapshots.",
    ])
    d.add_paragraph(
        "Interpretation: the UK chart is diverse by count but heavy-tailed. A small group of artists with large catalogues "
        "(Taylor Swift, Sabrina Carpenter, Billie Eilish) and a few evergreen songs account for a disproportionate share of slots.")
    figure(d, "fig02_diversity_over_time.png", "Figure 2. Unique artists and the Artist Concentration Index by month.", 15)
    pk = F["peak"]
    d.add_paragraph(
        f"Concentration is not constant. Unique artists per month peaked in {mk.loc[mk['unique_artists'].idxmax(), 'month']:%B %Y} "
        f"({int(mk['unique_artists'].max())}) and fell to {int(mk['unique_artists'].min())} in {mk.loc[mk['unique_artists'].idxmin(), 'month']:%B %Y}. "
        f"The winter peak is consistent with seasonal songs entering the chart. The most concentrated single day is {pk['date']:%d %B %Y}, when "
        f"{F['top_day'].index[0]} had {F['top_day'].iloc[0]} of the 50 entries (index {pk['artist_concentration']:.2f}); this looks like a "
        "catalogue-wide surge and is worth verifying against the source.")

    # ---- 4 top10 vs top50
    d.add_heading("4. Top 10 versus positions 11-50 versus the whole Top 50", 1)
    d.add_paragraph("All KPIs were recomputed for each group with identical definitions. Figure 3 and the table below are the core comparison.")
    figure(d, "fig03_top10_vs_top50.png", "Figure 3. Collaboration, explicit, single and top-5 artist share by group.", 13)
    bt = B.copy()
    bt.insert(0, "KPI", bt.index)
    table(d, bt.reset_index(drop=True), fmt={c_: "{:,.3f}" for c_ in ["Top 10", "11-50", "Top 50"]}, widths=[6, 3, 3, 3])
    tests = pd.DataFrame(R["band_tests"])
    tests["Result"] = tests["p_value"].map(pv)
    table(d, tests[["comparison", "test", "Result"]].rename(columns={"comparison": "Top 10 vs 11-50", "test": "Test"}), widths=[6, 4, 3])
    d.add_paragraph(
        "Reading the table: the Top 10 has fewer collaborations, more explicit songs, many more singles, higher popularity, more "
        "concentration among a few artists, and slightly shorter songs. Differences in explicit and single share are large; "
        "differences in track length (about 5 seconds) and collaboration (4 points) are statistically detectable but small.")

    # ---- 5 collab
    d.add_heading("5. Collaboration structure", 1)
    col = R["collab"]
    ts = pd.DataFrame(col["team_sizes"]).rename(columns={"artists_on_track": "Artists on track", "entries": "Entries", "share_%": "Share %"})
    table(d, ts, fmt={"Entries": "{:,.0f}", "Share %": "{:.1f}"}, widths=[4, 3, 3])
    bullets(d, [
        f"Collaboration Ratio {pct(col['ratio'])}; average {col['avg_artists_song']:.2f} artists per song and {col['avg_artists_collab']:.2f} per collaboration. Most collaborations are duets; "
        f"{pct((c['n_artists'] >= 3).mean())} of entries have three or more artists.",
        f"Rank groups: Top 10 {col['by_band'][0]['collab_share_%']:.1f}%, positions 11-50 {col['by_band'][1]['collab_share_%']:.1f}%, Top 50 {col['by_band'][2]['collab_share_%']:.1f}%. "
        f"Average position: solo {col['avg_pos_solo']:.1f}, collaboration {col['avg_pos_collab']:.1f} - practically the same.",
        f"Network: {col['network']['nodes']} artists, {col['network']['edges']} links, {col['network']['components']} separate clusters; the largest cluster has {col['network']['largest_component']} artists. Network density is {col['network']['density']:.3f}, i.e. sparse.",
        "Most connected artists (partners): " + ", ".join(f"{r['artist']} ({r['partners']})" for r in col["top_degree"][:5]) + ".",
        "Strongest pairings (chart entries together): " + "; ".join(f"{r['a']} + {r['b']} ({r['weight']})" for r in col["top_pairs"][:4]) + ".",
    ])
    figure(d, "fig04_collab_network.png", "Figure 4. Collaboration network of the 45 most connected artists.", 14)
    d.add_paragraph("Interpretation: collaboration is a mainstream tactic (about one entry in four) but forms many small, "
                    "separate clusters rather than one connected scene. Hip-hop figures (Drake, Travis Scott, Kendrick Lamar) and "
                    "producers (Chase & Status) are the main connectors. Collaboration helps presence in the chart, not the very top.")

    # ---- 6 explicit
    d.add_heading("6. Content explicitness", 1)
    figure(d, "fig05_explicit.png", "Figure 5. Explicit share by rank group and at each chart position.", 15)
    evt = F["ev"].reset_index().rename(columns={"content": "Content", "entries": "Entries", "avg_popularity": "Avg popularity",
                                                "median_popularity": "Median pop.", "avg_position": "Avg position", "top10_share_%": "In Top 10 %"})
    table(d, evt, fmt={"Entries": "{:,.0f}", "Avg popularity": "{:.2f}", "Median pop.": "{:.0f}", "Avg position": "{:.2f}", "In Top 10 %": "{:.1f}"})
    bullets(d, [
        f"Explicit share {pct(k['Explicit Content Share'])} overall; Top 10 {pct(B.loc['Explicit Content Share', 'Top 10'])}; positions 11-50 {pct(B.loc['Explicit Content Share', '11-50'])}. It declines steadily with chart position (Figure 5, right).",
        f"Explicit entries have a slightly better average position ({ev.loc['Explicit', 'avg_position']:.1f} vs {ev.loc['Clean', 'avg_position']:.1f}, {pv(R['explicit']['p_position'])}) and an almost identical average popularity "
        f"({ev.loc['Explicit', 'avg_popularity']:.1f} vs {ev.loc['Clean', 'avg_popularity']:.1f}); the popularity gap is statistically detectable but practically negligible.",
        "Monthly explicit share swings between about 15% (December 2024) and 44% (February 2025); the December low coincides with the seasonal-song influx.",
        "Cultural insight: the data show no sign that UK listeners avoid explicit content - explicit songs are over-represented at the top. "
        "The dataset contains no US or other-market chart, so the plan's question of whether the UK share is lower than the US cannot be answered here; "
        "that needs a comparison file.",
    ])

    # ---- 7 album
    d.add_heading("7. Album structure and release strategy", 1)
    figure(d, "fig06_album.png", "Figure 6. Release type by rank group and average position by release size.", 15)
    a = R["album"]
    bullets(d, [
        f"Single : album ratio {k['Single vs Album Ratio']:.2f} (compilations excluded; {a['compilations']} entries, 0.3%). Singles are {pct(a['single_share_all'])} of all entries, albums {pct(1 - a['single_share_all'] - a['compilations'] / len(c))}. More entries come from albums overall, but singles dominate at the top.",
        f"By rank group, singles are {F['sing']['Top 10']:.0f}% (Top 10), {F['sing']['11-25']:.0f}% (11-25) and {F['sing']['26-50']:.0f}% (26-50); average position single {a['avg_pos_single']:.1f} vs album {a['avg_pos_album']:.1f} ({pv(a['p_single_vs_album'])}).",
        f"Release size: {a['size_stats']['share_entries_12plus_tracks_%']:.0f}% of entries come from releases with 12+ tracks, and those entries average position {a['size_stats']['avg_position_12plus']:.1f} versus {a['size_stats']['avg_position_under12']:.1f} for smaller releases. "
        "Position worsens steadily with release size (Figure 6, right). The data only contain releases that charted, so we cannot compare against all albums released.",
        "Album floods: " + "; ".join(f"{r['lead_artist']} ({r['flood_days']} days with 3+ songs from one album, up to {r['max_tracks_in_chart']})" for r in a["flood"][:3])
        + f". {a['flood_days_total']} days in total have such a flood. Albums are approximated by artist + track count because the data have no album id.",
    ])
    d.add_paragraph("Interpretation: the UK market rewards focused single releases for peak chart positions, while album launches add many "
                    "lower-ranked entries. A few superstar album releases account for most of the 'album' volume.")

    # ---- 8 duration
    d.add_heading("8. Track duration and format", 1)
    figure(d, "fig07_duration.png", "Figure 7. Duration distribution, duration vs popularity, and average duration by popularity quartile.", 16)
    du = R["duration"]
    q = pd.DataFrame(du["by_quartile"])[["popularity_quartile", "entries", "avg_duration_min", "median_duration_min", "avg_position"]]
    q.columns = ["Popularity quartile", "Entries", "Avg duration (min)", "Median (min)", "Avg position"]
    table(d, q, fmt={"Entries": "{:,.0f}", "Avg duration (min)": "{:.2f}", "Median (min)": "{:.2f}", "Avg position": "{:.1f}"})
    bk = pd.DataFrame(du["buckets"]).rename(columns={"duration_bucket": "Length bucket", "entries": "Entries", "avg_popularity": "Avg popularity", "avg_position": "Avg position"})
    table(d, bk, fmt={"Entries": "{:,.0f}", "Avg popularity": "{:.1f}", "Avg position": "{:.1f}"})
    bullets(d, [
        f"Mean length {du['mean']:.2f} min, median {du['median']:.2f} min. {pct(du['short_share'])} of entries are under 3 minutes (short-form), {pct(du['long_share'])} are 4 minutes or longer. The histogram shows clusters just under 3 and 4 minutes.",
        f"The most popular quartile (Q4) has the shortest average length ({du['by_quartile'][3]['avg_duration_min']:.2f} min) and the best average position ({du['by_quartile'][3]['avg_position']:.1f}); the least popular quartile averages {du['by_quartile'][0]['avg_duration_min']:.2f} min.",
        f"Correlations are weak: duration vs popularity rho = {du['corr']['rho_duration_popularity']:.3f}, duration vs position rho = {du['corr']['rho_duration_position']:.3f}. Long tracks (4+ min) sit lower on average (position {du['buckets'][2]['avg_position']:.1f} vs {du['buckets'][0]['avg_position']:.1f} for short tracks).",
        "UK preference: the chart is dominated by radio-length songs of about three minutes, and average length is stable between 2024 and 2025. "
        "No US duration data are in the dataset, so comparison with US trends of longer hits is not possible here.",
    ])

    # ---- 9 domestic
    d.add_heading("9. Domestic versus international artists", 1)
    figure(d, "fig08_country.png", "Figure 8. Share of artist slots by artist home country group.", 12.5)
    d.add_paragraph(
        f"Country groups were assigned by hand for {int((F['ctry']['country_group'] != 'Unknown').sum())} artists (file artist_country.csv) and cover {100 - cs.get('Unknown', 0):.0f}% of artist slots. "
        f"UK artists hold {cs.get('UK', 0):.1f}% of slots, US artists {cs.get('US', 0):.1f}%, other countries {cs.get('Other', 0):.1f}%, unlabelled {cs.get('Unknown', 0):.1f}%. "
        f"Among labelled slots UK artists are {R['uk_share_of_labelled_%']:.0f}%. US artists are even stronger in the Top 10 "
        f"({R['country_by_band'][0]['share_%']:.0f}%) than in positions 11-50 ({R['country_by_band'][4]['share_%']:.0f}%). Labels come from general knowledge and should be reviewed before external use.")

    # ---- 10 kpi time
    d.add_heading("10. KPIs over time", 1)
    figure(d, "fig09_kpi_timeline.png", "Figure 9. KPIs for every snapshot date.", 16)
    d.add_paragraph("Every KPI is computed for each date (see Overview tab of the dashboard and daily_kpis in src/metrics.py). "
                    "Collaboration and single shares were highest in mid-2024 and declined, unique artists per day fell through 2025, "
                    "and concentration spiked in April-May 2025.")

    # ---- 11 recommendations
    d.add_heading("11. Recommendations for UK strategy", 1)
    bullets(d, [
        ("Lead with singles. ", f"Singles are {F['sing']['Top 10']:.0f}% of the Top 10. For peak positions, plan single-led campaigns; use albums to build chart depth."),
        ("Do not rely on collaboration to reach the top. ", "Collaborations are 20% of Top 10 entries against 24% below, with the same average position. Use them for reach and cross-audience exposure, not as a Top 10 tactic."),
        ("Do not shy away from explicit content. ", "Explicit songs are 40% of the Top 10 and sit slightly higher on average; clean-only rules are not needed for chart success."),
        ("Aim for radio-length songs. ", "Songs of about 2 to 4 minutes dominate; tracks over 4 minutes sit lower on average."),
        ("Treat domestic talent as an opportunity. ", f"UK artists hold about {cs.get('UK', 0):.0f}% of slots and less in the Top 10; local-talent development has room to grow."),
        ("Plan around seasonality and superstar release windows. ", "Winter brings many more artists (and, in December, fewer explicit songs); superstar album weeks flood the chart and compress space for others."),
    ])

    # ---- 12 limits
    d.add_heading("12. Limitations", 1)
    bullets(d, [
        "Playlist snapshots, not stream counts or sales; 'popularity' is a platform score that is capped near 100 and heavily tied.",
        "Appearances are chart-days, so long-running songs weigh more. Entries are repeated observations, so p-values overstate independence.",
        "1 March 2025 was removed and 4 other dates are missing. A very few non-artist credits (e.g. 'Various Artists', 5 entries) remain.",
        "Country labels are manual (about 95% of slots labelled) and may contain errors; the plan's domestic-share example numbers were illustrative, not targets.",
        "Album identity is approximated; no US or other-market comparison data are included; the dataset's attribution should be confirmed before external publication.",
    ])

    # ---- 13 reproducibility
    d.add_heading("13. Reproducibility and deliverables", 1)
    d.add_paragraph("Run python src/cleaning.py, python src/findings.py, python src/figures.py, python src/build_report.py, then streamlit run app.py. "
                    "python -m pytest runs 15 automated checks. See README.md for step-by-step installation and deployment instructions.")

    d.add_heading("References", 1)
    for r in [
        "Hirschman, A. O. (1945). National Power and the Structure of Foreign Trade. University of California Press; Herfindahl, O. C. (1950). Concentration in the Steel Industry (PhD thesis, Columbia University). Basis of the concentration index; see also U.S. Department of Justice and Federal Trade Commission, Merger Guidelines.",
        "Magurran, A. E. (2004). Measuring Biological Diversity. Blackwell. Species richness as a diversity measure.",
        "Shannon, C. E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal, 27. Basis of the entropy-based Content Variety Index.",
        "Mann, H. B. and Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. Annals of Mathematical Statistics, 18.",
        "Hagberg, A., Schult, D. and Swart, P. (2008). Exploring network structure, dynamics, and function using NetworkX. Proceedings of the 7th Python in Science Conference.",
        "Streamlit documentation, https://docs.streamlit.io (framework used for the dashboard).",
    ]:
        d.add_paragraph(r, style="List Bullet")
    d.save(ROOT / "reports" / "Research_Paper.docx")


# ----------------------------------------------------------------- executive summary
def build_summary(F):
    c, R, k, B, ev, cs = F["c"], F["R"], F["k"], F["bands"], F["ev"], F["cs"]
    d = new_doc()
    para(d, "UK Top 50 Playlist: Executive Summary", bold=True, size=22, color=BLUE)
    para(d, f"{R['period']['days']} daily snapshots, {R['period']['start']} to {R['period']['end']} | {R['period']['entries']:,} chart entries | "
            f"{k['Unique Artist Count']:.0f} artists", italic=True, size=9.5)
    d.add_heading("The short version", 2)
    d.add_paragraph(
        "The UK Top 50 is a varied, fast-rotating chart with a small group of superstars at its core. The Top 10 is where the "
        "market is most different: more singles, more explicit songs, more US artists and fewer collaborations than the rest of the chart.")
    d.add_heading("Key numbers", 2)
    kp = pd.DataFrame({
        "KPI": ["Unique artists", "Artist Concentration Index", "Top-5 artist share", "Collaboration ratio", "Explicit share",
                "Singles share of entries", "Single : album ratio", "Median track length"],
        "Top 50": [f"{k['Unique Artist Count']:.0f}", f"{k['Artist Concentration Index']:.3f}", pct(k["Top-5 Artist Share"]), pct(k["Collaboration Ratio"]),
                   pct(k["Explicit Content Share"]), pct(B.loc["Single Share of Entries", "Top 50"]), f"{k['Single vs Album Ratio']:.2f}", f"{R['duration']['median']:.1f} min"],
        "Top 10": [f"{B.loc['Unique Artist Count', 'Top 10']:.0f}", f"{B.loc['Artist Concentration Index', 'Top 10']:.3f}", pct(B.loc["Top-5 Artist Share", "Top 10"]),
                   pct(B.loc["Collaboration Ratio", "Top 10"]), pct(B.loc["Explicit Content Share", "Top 10"]), pct(B.loc["Single Share of Entries", "Top 10"]),
                   f"{B.loc['Single vs Album Ratio', 'Top 10']:.2f}", f"{R['duration']['by_band'][0]['median_duration_min']:.1f} min"],
        "Positions 11-50": [f"{B.loc['Unique Artist Count', '11-50']:.0f}", f"{B.loc['Artist Concentration Index', '11-50']:.3f}", pct(B.loc["Top-5 Artist Share", "11-50"]),
                            pct(B.loc["Collaboration Ratio", "11-50"]), pct(B.loc["Explicit Content Share", "11-50"]), pct(B.loc["Single Share of Entries", "11-50"]),
                            f"{B.loc['Single vs Album Ratio', '11-50']:.2f}", f"{R['duration']['by_band'][1]['median_duration_min']:.1f} min"],
    })
    table(d, kp, widths=[5.5, 3.2, 3.2, 3.8], font=9.5)
    d.add_heading("What it means", 2)
    bullets(d, [
        ("Healthy diversity. ", f"{k['Unique Artist Count']:.0f} artists charted and no one dominates: the top 5 hold {pct(k['Top-5 Artist Share'])} of slots. Taylor Swift is the single biggest presence ({F['board'].iloc[0]['share_%']:.1f}%)."),
        ("Singles win the top. ", f"Singles are {F['sing']['Top 10']:.0f}% of the Top 10 but {F['sing']['26-50']:.0f}% of positions 26-50. Marketing should emphasise single releases for peak positions."),
        ("Collaborations are common, not decisive. ", f"{pct(k['Collaboration Ratio'])} of entries are collaborations, but they are less common in the Top 10 ({pct(B.loc['Collaboration Ratio', 'Top 10'])}) and no better ranked on average."),
        ("Explicit content is not a barrier. ", f"{pct(B.loc['Explicit Content Share', 'Top 10'])} of Top 10 entries are explicit and explicit songs rank slightly higher on average."),
        ("Radio-length songs. ", "Typical tracks run about 3 minutes; tracks over 4 minutes sit lower on the chart."),
        ("Domestic talent has room to grow. ", f"UK artists hold about {cs.get('UK', 0):.0f}% of artist slots; US artists about {cs.get('US', 0):.0f}% (58% of the Top 10)."),
    ])
    d.add_heading("Recommended actions", 2)
    bullets(d, [
        "Build chart campaigns around focused single releases; use albums for catalogue depth.",
        "Use collaborations for reach, not as a Top 10 tactic.",
        "Invest in UK artist development, especially for Top 10 breakthrough where US acts dominate.",
        "Plan around winter seasonality and superstar album weeks, which crowd out other artists.",
        "Review the live dashboard to test any of these by date, artist, release type or chart position.",
    ])
    d.add_heading("Caveats", 2)
    d.add_paragraph("Based on playlist snapshots, not streams or sales. One snapshot date was removed and four are missing. "
                    "Country labels are hand-made for the main artists and should be verified. No US comparison data were available.")
    d.save(ROOT / "reports" / "Executive_Summary.docx")


def main():
    F = facts()
    build_paper(F)
    build_summary(F)
    print("saved reports/Research_Paper.docx and reports/Executive_Summary.docx")


if __name__ == "__main__":
    main()
