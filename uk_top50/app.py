"""UK Top 50 Playlist - Market Structure, Artist Diversity & Content Localization.

Run:  streamlit run app.py
"""
import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402
import metrics as m  # noqa: E402

st.set_page_config(page_title="UK Top 50 Market Structure", page_icon="🎧", layout="wide")

BLUE, GREY, ORANGE, TEAL = "#1F5FBF", "#9AA5B1", "#D9622B", "#1B8A78"
BAND_COLORS = {"Top 10": BLUE, "11-50": GREY, "Top 50": TEAL}


# ---------------------------------------------------------------- data
@st.cache_data
def load():
    return data.load_clean(), data.load_countries()


@st.cache_data
def artist_list(_clean):
    return sorted(data.explode_artists(_clean)["artist_name"].unique(), key=str.lower)


clean_all, countries = load()

# ---------------------------------------------------------------- sidebar filters
st.sidebar.title("Filters")
dmin, dmax = clean_all["date"].min().date(), clean_all["date"].max().date()
date_range = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax,
                                   help="Pick a start AND an end date.")
if not (isinstance(date_range, (tuple, list)) and len(date_range) == 2):
    st.info("Please pick both a start and an end date in the sidebar.")
    st.stop()
start, end = date_range

artist_pick = st.sidebar.multiselect("Artist (keeps songs they are on)", artist_list(clean_all))
mode = st.sidebar.radio("Track type", ["All", "Solo only", "Collaborations only"])
types = sorted(clean_all["album_type"].unique())
type_pick = st.sidebar.multiselect("Album type", types, default=types,
                                   help="album, single or compilation. Choose 'single' only to see singles only.")
scope = st.sidebar.radio("Chart positions", ["Top 50", "Top 10", "Positions 11-50"],
                         help="Applies to every tab except 'Top 10 vs Top 50', which always compares them.")

base = clean_all[(clean_all["date"].dt.date >= start) & (clean_all["date"].dt.date <= end)]
base = base[base["album_type"].isin(type_pick)]
if mode == "Solo only":
    base = base[~base["is_collab"]]
elif mode == "Collaborations only":
    base = base[base["is_collab"]]
if artist_pick:
    wanted = set(artist_pick)
    base = base[base["artist_list"].apply(lambda s: bool(wanted & set(s.split(" | "))))]

if scope == "Top 10":
    clean = base[base["position"] <= 10]
elif scope == "Positions 11-50":
    clean = base[base["position"] > 10]
else:
    clean = base

st.title("🎧 UK Top 50 - Market Structure & Content Localization")
st.caption("Daily UK Top 50 playlist snapshots, May 2024 - Nov 2025 (provided dataset). "
           "Use the sidebar to change the period, artists, track type, release type and chart positions.")

if clean.empty:
    st.warning("No data for these filters. Please widen the date range or remove a filter.")
    st.stop()

exploded = data.explode_artists(clean)
base_exploded = data.explode_artists(base)
st.sidebar.markdown(f"**{len(clean):,}** chart entries  \n**{clean['date'].nunique()}** days  \nScope: **{scope}**")

tabs = st.tabs(["Overview", "Top 10 vs Top 50", "Artist dominance", "Collaboration",
                "Explicit vs clean", "Album type", "Track duration", "Help & definitions"])

# ---------------------------------------------------------------- overview
with tabs[0]:
    k = m.headline_kpis(clean, exploded)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Artist Concentration Index", f"{k['Artist Concentration Index']:.3f}",
              help="Sum of squared artist shares (HHI, 0-1). Higher = a few artists dominate.")
    c2.metric("Unique Artist Count", f"{k['Unique Artist Count']:,}", help="Distinct artists in the selection.")
    c3.metric("Collaboration Ratio", f"{k['Collaboration Ratio']:.1%}", help="Songs with 2+ artists / all songs.")
    c4.metric("Explicit Content Share", f"{k['Explicit Content Share']:.1%}")
    c5, c6, c7, c8 = st.columns(4)
    sva = k["Single vs Album Ratio"]
    c5.metric("Single vs Album Ratio", "n/a" if pd.isna(sva) else f"{sva:.2f}",
              help="Singles / albums (compilations excluded). Below 1 = albums appear more.")
    c6.metric("Content Variety Index", f"{k['Content Variety Index']:.2f}",
              help="0-1. Balance (normalised Shannon entropy) of artists, release type, explicit and duration mix.")
    c7.metric("Top-5 Artist Share", f"{k['Top-5 Artist Share']:.1%}",
              help="Share of artist slots held by the 5 most frequent artists.")
    c8.metric("Daily Diversity Ratio", f"{k['Daily Diversity Ratio']:.2f}",
              help="Unique artists / artist slots on one day, averaged over days (different from the period-wide Concentration Index).")
    v = k["Content Variety Index"]
    st.caption(f"Content variety is **{'balanced' if v > 0.75 else 'moderate' if v > 0.5 else 'skewed'}** "
               f"(>0.75 balanced, <0.5 skewed). Normalised concentration: {k['Normalised Concentration']:.4f}.")

    st.subheader("KPIs over time")
    grain = st.radio("Time step", ["Daily (14-day average)", "Monthly"], horizontal=True)
    if grain.startswith("Daily"):
        kp = m.daily_kpis(clean, exploded).set_index("date")
        kp_plot = kp.rolling(14, min_periods=1).mean().reset_index()
        xcol = "date"
    else:
        kp_plot = m.monthly_kpis(clean, exploded)
        xcol = "month"
    names = {"artist_concentration": "Artist Concentration Index", "unique_artists": "Unique artists",
             "collaboration_ratio": "Collaboration Ratio", "explicit_share": "Explicit Content Share",
             "single_share": "Singles share of entries", "single_vs_album_ratio": "Single vs Album Ratio",
             "content_variety": "Content Variety Index", "top5_share": "Top-5 Artist Share",
             "avg_duration_min": "Average duration (min)"}
    pick = st.multiselect("KPIs to plot (each in its own chart)", list(names.values()),
                          default=["Artist Concentration Index", "Unique artists", "Collaboration Ratio",
                                   "Explicit Content Share"])
    inv = {v2: k2 for k2, v2 in names.items()}
    cols = st.columns(2)
    for i, nm in enumerate(pick):
        cols[i % 2].plotly_chart(px.line(kp_plot, x=xcol, y=inv[nm], title=nm, labels={inv[nm]: "", xcol: ""},
                                         color_discrete_sequence=[BLUE]), width="stretch")
    with st.expander("Download KPI table (CSV)"):
        st.dataframe(kp_plot, hide_index=True, width="stretch")
        st.download_button("Download CSV", kp_plot.to_csv(index=False), "uk_top50_kpis.csv", "text/csv")

# ---------------------------------------------------------------- top 10 vs top 50
with tabs[1]:
    st.subheader("Top 10 vs positions 11-50 vs whole Top 50")
    st.write("Same KPI definitions for each group. This tab ignores the 'Chart positions' filter "
             "but respects all other filters.")
    if (base["position"] <= 10).sum() == 0 or (base["position"] > 10).sum() == 0:
        st.info("The current filters leave no entries in one of the groups.")
    else:
        bt = m.kpis_by_band(base, base_exploded)
        show = bt.copy()
        st.dataframe(show.style.format("{:,.3f}"), width="stretch")
        pct_rows = ["Collaboration Ratio", "Explicit Content Share", "Single Share of Entries", "Top-5 Artist Share"]
        long = bt.loc[pct_rows].mul(100).reset_index().melt(id_vars="index", var_name="group", value_name="share")
        l, r = st.columns(2)
        l.plotly_chart(px.bar(long, x="index", y="share", color="group", barmode="group", text_auto=".0f",
                              color_discrete_map=BAND_COLORS, labels={"index": "", "share": "Share (%)"},
                              title="Shares by group"), width="stretch")
        cs = m.country_share_by_band(base_exploded, countries)
        r.plotly_chart(px.bar(cs, x="share_%", y="group", color="country_group", orientation="h",
                              category_orders={"group": ["Top 10", "11-50", "Top 50"]},
                              color_discrete_map={"UK": BLUE, "US": ORANGE, "Other": TEAL, "Unknown": "#C9CED6"},
                              title="Domestic (UK) vs international artists", labels={"share_%": "% of artist slots", "group": ""}),
                       width="stretch")
        l2, r2 = st.columns(2)
        ab = base.assign(rank_band=base["position"].map(lambda p: "Top 10" if p <= 10 else "11-50"))
        tt = ab.groupby(["rank_band", "album_type"]).size().reset_index(name="n")
        tt["share"] = tt["n"] / tt.groupby("rank_band")["n"].transform("sum") * 100
        l2.plotly_chart(px.bar(tt, x="rank_band", y="share", color="album_type", text_auto=".0f",
                               title="Release type by group (% of entries)",
                               labels={"rank_band": "", "share": "%"}), width="stretch")
        dur = m.duration_by_rank_group(base)
        r2.plotly_chart(px.bar(dur, x="group", y="avg_duration_min", text_auto=".2f",
                               color="group", color_discrete_map=BAND_COLORS,
                               title="Average track length (min)", labels={"group": "", "avg_duration_min": "Minutes"}),
                        width="stretch")
        st.markdown("**Are the Top 10 / 11-50 differences real?** Statistical tests on the current selection:")
        bt_tests = m.band_tests(base)
        bt_tests["significant (p<0.05)"] = bt_tests["p_value"] < 0.05
        st.dataframe(bt_tests.style.format({"statistic": "{:,.1f}", "p_value": "{:.2e}"}),
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- artists
with tabs[2]:
    st.subheader("Artist dominance leaderboard")
    board = m.appearance_counts(exploded)
    n_show = st.slider("How many artists to show", 5, 30, 15)
    top = board.head(n_show)
    fig = px.bar(top.iloc[::-1], x="appearances", y="artist_name", orientation="h",
                 hover_data=["days_on_chart", "unique_songs", "avg_position", "share_%"],
                 labels={"artist_name": "", "appearances": "Chart appearances (days x songs)"},
                 color_discrete_sequence=[BLUE])
    st.plotly_chart(fig, width="stretch")
    st.caption(f"The top 5 artists hold {m.top_n_share(exploded, 5):.1%} of all artist slots; "
               f"the whole selection has {m.unique_artist_count(exploded):,} different artists.")
    st.dataframe(board, width="stretch", hide_index=True)

    st.subheader("Domestic vs international artists")
    cs = m.country_share(exploded, countries)
    l, r = st.columns(2)
    l.plotly_chart(px.pie(cs, names="country_group", values="appearances", hole=0.45,
                          color="country_group",
                          color_discrete_map={"UK": BLUE, "US": ORANGE, "Other": TEAL, "Unknown": "#C9CED6"}),
                   width="stretch")
    known = cs[cs["country_group"] != "Unknown"]["share_%"].sum()
    r.info(f"Country labels were added by hand for the {int((countries['country_group'] != 'Unknown').sum())} "
           f"most frequent artists and cover **{known:.0f}%** of appearances in this selection. "
           "'Other' = neither UK nor US. 'Unknown' = not labelled yet. Edit `artist_country.csv` to improve this.")

# ---------------------------------------------------------------- collaboration
with tabs[3]:
    st.subheader("Solo vs collaboration")
    l, r = st.columns(2)
    solo_collab = clean["is_collab"].map({True: "Collaboration", False: "Solo"}).value_counts().reset_index()
    solo_collab.columns = ["type", "entries"]
    l.plotly_chart(px.pie(solo_collab, names="type", values="entries", hole=0.45,
                          title="Share of chart entries"), width="stretch")
    cr = m.collab_by_rank_group(base)
    r.plotly_chart(px.bar(cr, x="group", y="collab_share_%", text_auto=".1f", color="group",
                          color_discrete_map=BAND_COLORS,
                          title="Collaboration share: Top 10 vs 11-50 vs Top 50 (ignores position filter)",
                          labels={"group": "", "collab_share_%": "Collaboration share (%)"}), width="stretch")
    a, b, c_ = st.columns(3)
    a.metric("Average artists per song", f"{m.avg_collaborators(clean):.2f}")
    b.metric("Average artists per collaboration", f"{m.avg_artists_per_collab(clean):.2f}"
             if clean["is_collab"].any() else "n/a")
    c_.metric("Songs with 3+ artists", f"{(clean['n_artists'] >= 3).mean():.1%}")
    st.dataframe(m.team_size_distribution(clean), hide_index=True, width="stretch")

    st.subheader("Collaboration network")
    edges = m.collab_edges(clean)
    if edges.empty:
        st.info("No collaborations in the current selection.")
    else:
        max_nodes = st.slider("Max artists in the graph", 10, 80, 40)
        min_w = st.slider("Minimum chart entries together to draw a link", 1, 100, 5)
        e2 = edges[edges["weight"] >= min_w]
        G = nx.Graph()
        for _, row in e2.iterrows():
            G.add_edge(row["a"], row["b"], weight=row["weight"])
        if G.number_of_nodes() == 0:
            st.info("No links at this minimum. Lower the slider.")
        else:
            strength = dict(G.degree(weight="weight"))
            keep = sorted(strength, key=strength.get, reverse=True)[:max_nodes]
            G = G.subgraph(keep).copy()
            pos = m.component_layout(G)
            ex, ey = [], []
            for u, v2 in G.edges():
                ex += [pos[u][0], pos[v2][0], None]
                ey += [pos[u][1], pos[v2][1], None]
            size_map = exploded["artist_name"].value_counts()
            nodes = list(G.nodes())
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=0.8, color="#999"), hoverinfo="none"))
            fig.add_trace(go.Scatter(
                x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes], mode="markers+text",
                text=[n if G.degree(n) >= 2 else "" for n in nodes], textposition="top center",
                marker=dict(size=[8 + size_map.get(n, 1) ** 0.5 for n in nodes],
                            color=[G.degree(n) for n in nodes], colorscale="Viridis", colorbar=dict(title="Partners")),
                hovertext=[f"{n}<br>{size_map.get(n, 0)} appearances<br>{G.degree(n)} partners" for n in nodes],
                hoverinfo="text"))
            fig.update_layout(showlegend=False, height=600, margin=dict(l=0, r=0, t=10, b=0),
                              xaxis=dict(visible=False), yaxis=dict(visible=False))
            st.plotly_chart(fig, width="stretch")
            st.caption("Dot size = chart appearances. Colour = number of partners. Names shown for artists with 2+ partners.")
        ns = m.network_stats(edges)
        n1, n2, n3 = st.columns(3)
        n1.metric("Artists in network", ns["nodes"])
        n2.metric("Collaboration links", ns["edges"])
        n3.metric("Separate clusters", ns["components"])
        l3, r3 = st.columns(2)
        l3.markdown("**Most connected artists (node degree)**")
        l3.dataframe(ns["top_degree"].rename(columns={"partners": "Different partners",
                                                      "weighted_degree": "Chart entries together"}),
                     hide_index=True, width="stretch")
        r3.markdown("**Strongest pairs**")
        r3.dataframe(edges.head(10).rename(columns={"a": "Artist A", "b": "Artist B", "weight": "Entries together"}),
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- explicit
with tabs[4]:
    st.subheader("Explicit vs clean content")
    l, r = st.columns(2)
    ex_pie = clean["is_explicit"].map({True: "Explicit", False: "Clean"}).value_counts().reset_index()
    ex_pie.columns = ["type", "entries"]
    l.plotly_chart(px.pie(ex_pie, names="type", values="entries", hole=0.45, title="Overall share"), width="stretch")
    eg = m.explicit_by_rank_group(base)
    cnt = base.assign(group=base["position"].map(lambda p: "Top 10" if p <= 10 else "11-50"),
                      type=base["is_explicit"].map({True: "Explicit", False: "Clean"})) \
        .groupby(["group", "type"]).size().reset_index(name="entries")
    r.plotly_chart(px.bar(cnt, x="group", y="entries", color="type", barmode="group",
                          title="Explicit vs clean counts: Top 10 vs 11-50", labels={"group": ""}), width="stretch")
    st.dataframe(eg, hide_index=True, width="stretch")
    l2, r2 = st.columns(2)
    ep = m.explicit_by_position(clean)
    if len(ep) > 2:
        l2.plotly_chart(px.scatter(ep, x="position", y="explicit_share_%", trendline="ols",
                                   title="Explicit share at each chart position"), width="stretch")
    r2.plotly_chart(px.line(m.explicit_monthly(clean), x="month", y="explicit_share_%",
                            title="Explicit share by month", markers=True), width="stretch")
    st.subheader("Does explicit content matter? Popularity and chart position")
    evc = m.explicit_vs_clean_popularity(clean)
    st.dataframe(evc, hide_index=True, width="stretch")
    l3, r3 = st.columns(2)
    l3.plotly_chart(px.bar(evc, x="content", y="avg_popularity", text_auto=".1f", title="Average popularity",
                           labels={"content": "", "avg_popularity": "Popularity (0-100)"}), width="stretch")
    r3.plotly_chart(px.bar(evc, x="content", y="avg_position", text_auto=".1f",
                           title="Average chart position (lower = higher on chart)",
                           labels={"content": "", "avg_position": "Position"}), width="stretch")

# ---------------------------------------------------------------- album type
with tabs[5]:
    st.subheader("Single vs album")
    l, r = st.columns(2)
    at = m.album_type_share(clean)
    l.plotly_chart(px.pie(at, names="album_type", values="entries", hole=0.45,
                          title="Chart entries by release type"), width="stretch")
    by_rank = m.album_type_by_rank(base)
    r.plotly_chart(px.bar(by_rank, x="rank_group", y="entries", color="album_type", barmode="group",
                          title="Release type by rank group", labels={"rank_group": ""}), width="stretch")
    st.caption("The Single vs Album Ratio leaves out compilations "
               f"({int((clean['album_type'] == 'compilation').sum())} entries here) so it compares like with like.")
    sb = m.album_size_summary(clean)
    l2, r2 = st.columns(2)
    l2.plotly_chart(px.bar(sb, x="album_size_bucket", y="entries", title="Entries by release size (tracks on release)",
                           labels={"album_size_bucket": "Tracks on the release"}), width="stretch")
    r2.plotly_chart(px.bar(sb, x="album_size_bucket", y="avg_position", text_auto=".1f",
                           title="Average chart position by release size (lower is better)",
                           labels={"album_size_bucket": "Tracks on the release"}), width="stretch")
    st.subheader("Do big album launches flood the chart?")
    fl = m.album_flood_summary(clean)
    if fl.empty:
        st.info("No day in this selection has 3+ songs from the same album.")
    else:
        st.write("Days with 3+ songs from the same artist's album (album approximated by artist + track count).")
        st.dataframe(fl.head(15), hide_index=True, width="stretch")

# ---------------------------------------------------------------- duration
with tabs[6]:
    st.subheader("Track duration")
    l, r = st.columns(2)
    l.plotly_chart(px.histogram(clean, x="duration_min", nbins=40, title="Track length (minutes)",
                                labels={"duration_min": "Minutes"}, color_discrete_sequence=[BLUE]), width="stretch")
    ds = m.duration_summary(clean)
    r.plotly_chart(px.bar(ds, x="duration_bucket", y="avg_popularity", text_auto=".1f",
                          title="Average popularity by length bucket (short <3, medium 3-4, long >4 min)",
                          labels={"duration_bucket": "", "avg_popularity": "Avg popularity"}), width="stretch")
    l2, r2 = st.columns(2)
    sample = clean.dropna(subset=["popularity"])
    sample = sample.sample(min(len(sample), 5000), random_state=1)
    l2.plotly_chart(px.scatter(sample, x="duration_min", y="popularity", opacity=0.3,
                               title="Duration vs popularity (up to 5,000 sampled entries)",
                               labels={"duration_min": "Minutes", "popularity": "Popularity"}), width="stretch")
    q = m.duration_by_popularity_quartile(clean.dropna(subset=["popularity"]))
    r2.plotly_chart(px.bar(q, x="popularity_quartile", y="avg_duration_min", text_auto=".2f",
                           title="Average length by popularity quartile",
                           labels={"popularity_quartile": "Popularity quartile", "avg_duration_min": "Minutes"}),
                    width="stretch")
    corr = m.duration_correlations(clean)
    st.caption(f"Spearman correlation: duration vs popularity {corr['rho_duration_popularity']:.3f}, "
               f"duration vs chart position {corr['rho_duration_position']:.3f} "
               "(near 0 = length barely matters).")
    st.dataframe(q, width="stretch", hide_index=True)
    monthly = clean.assign(month=clean["date"].dt.to_period("M").dt.to_timestamp()) \
        .groupby("month")["duration_min"].mean().reset_index()
    st.plotly_chart(px.line(monthly, x="month", y="duration_min", markers=True,
                            title="Average track length by month (minutes)"), width="stretch")
    st.caption("Popularity of 0 in the raw data is treated as missing and ignored. "
               "Popularity quartiles are equal-size groups computed over the whole dataset.")

# ---------------------------------------------------------------- help
with tabs[7]:
    st.subheader("How to use this dashboard")
    st.markdown("""
1. Use the **sidebar** to choose dates, artists, solo/collaboration, release type and chart positions.
2. The **Overview** tab shows the seven KPIs and how they move over time.
3. **Top 10 vs Top 50** compares the very top of the chart with the rest.
4. Other tabs go deeper on artists, collaborations, explicit content, release type and duration.

**KPI definitions**

| KPI | Meaning |
|---|---|
| Artist Concentration Index | Sum of squared artist shares (HHI). 0 = very spread out, 1 = one artist |
| Unique Artist Count | Distinct artists (richness) |
| Collaboration Ratio | Songs with 2+ artists / all songs |
| Explicit Content Share | Explicit entries / all entries |
| Single vs Album Ratio | Singles / albums (compilations excluded) |
| Content Variety Index | Average normalised Shannon entropy of artists, release type, explicit mix, duration mix |
| Top-5 Artist Share | Share of artist slots held by the 5 most frequent artists |
| Daily Diversity Ratio | Unique artists / artist slots on one day, averaged over days |

**Good to know**
- Data are playlist snapshots, not stream counts. "Appearances" are chart-days, so long-running songs weigh more.
- 1 March 2025 was removed (two mixed snapshots) and 4 other dates are missing in the source.
- Country labels are hand-made for the most frequent artists and should be checked.
""")
