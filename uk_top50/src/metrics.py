"""Step 2 - KPI and analysis functions (used by findings, figures, the paper and the app).

Two tables are used:
  clean    one row per chart entry (a song on a day)
  exploded one row per chart entry per artist (a collaboration counts once per artist)

Metric vocabulary (one definition each, so the paper and dashboard agree)
  Unique Artist Count        distinct artists in the selection ("richness")
  Artist Concentration Index sum of squared artist shares of artist slots (HHI, 0..1)
  Normalised Concentration   (HHI - 1/N) / (1 - 1/N), N = unique artists
  Top-5 Artist Share         share of artist slots held by the 5 most frequent artists
  Daily Diversity Ratio      unique artists / artist slots on ONE day, averaged over days
"""
import numpy as np
import pandas as pd
from scipy import stats

from data import BAND_ORDER, DUR_ORDER, POP_ORDER, SIZE_ORDER  # noqa: F401


# ----------------------------------------------------------------- artist dominance and diversity
def appearance_counts(exploded: pd.DataFrame) -> pd.DataFrame:
    g = exploded.groupby("artist_name")
    out = pd.DataFrame({
        "appearances": g.size(),
        "days_on_chart": g["date"].nunique(),
        "unique_songs": g["song"].nunique(),
        "avg_position": g["position"].mean().round(1),
        "best_position": g["position"].min(),
    }).sort_values(["appearances", "unique_songs"], ascending=False)
    out["share_%"] = (out["appearances"] / out["appearances"].sum() * 100).round(2)
    return out.reset_index()


def concentration_index(exploded: pd.DataFrame) -> float:
    """Artist Concentration Index = sum of squared appearance shares (HHI)."""
    if exploded.empty:
        return np.nan
    shares = exploded["artist_name"].value_counts(normalize=True)
    return float((shares ** 2).sum())


def normalised_concentration(exploded: pd.DataFrame) -> float:
    n = exploded["artist_name"].nunique()
    if exploded.empty or n <= 1:
        return np.nan
    return (concentration_index(exploded) - 1 / n) / (1 - 1 / n)


def top_n_share(exploded: pd.DataFrame, n: int = 5) -> float:
    c = exploded["artist_name"].value_counts()
    return float(c.head(n).sum() / c.sum()) if c.sum() else np.nan


def unique_artist_count(exploded: pd.DataFrame) -> int:
    return int(exploded["artist_name"].nunique())


def daily_unique_artists(exploded: pd.DataFrame) -> pd.Series:
    return exploded.groupby("date")["artist_name"].nunique()


def daily_diversity(exploded: pd.DataFrame) -> pd.Series:
    """Unique artists / artist slots, for each day."""
    g = exploded.groupby("date")
    return g["artist_name"].nunique() / g.size()


def weekly_unique_artists(exploded: pd.DataFrame) -> pd.Series:
    return exploded.groupby(pd.Grouper(key="date", freq="W"))["artist_name"].nunique()


def daily_top5_share(exploded: pd.DataFrame) -> pd.Series:
    """Per day: share of the day's artist slots held by that day's 5 most frequent artists."""
    def f(s):
        c = s.value_counts()
        return c.head(5).sum() / c.sum()
    return exploded.groupby("date")["artist_name"].apply(f)


def share_held_by_period_top5(exploded: pd.DataFrame) -> pd.Series:
    """Per day: share of slots held by the 5 artists who dominate the whole selection."""
    top5 = exploded["artist_name"].value_counts().head(5).index
    return exploded.groupby("date")["artist_name"].apply(lambda s: s.isin(top5).mean())


# ----------------------------------------------------------------- collaboration
def collaboration_ratio(clean: pd.DataFrame) -> float:
    return float(clean["is_collab"].mean()) if len(clean) else np.nan


def avg_collaborators(clean: pd.DataFrame) -> float:
    """Average number of artists per song."""
    return float(clean["n_artists"].mean()) if len(clean) else np.nan


def avg_artists_per_collab(clean: pd.DataFrame) -> float:
    c = clean[clean["is_collab"]]
    return float(c["n_artists"].mean()) if len(c) else np.nan


def team_size_distribution(clean: pd.DataFrame) -> pd.DataFrame:
    t = clean["n_artists"].clip(upper=4).map(lambda n: "4+" if n >= 4 else str(n))
    c = t.value_counts().reindex(["1", "2", "3", "4+"]).fillna(0).astype(int)
    return pd.DataFrame({"artists_on_track": c.index, "entries": c.values,
                         "share_%": (c.values / max(c.sum(), 1) * 100).round(1)})


def split_by_band(df: pd.DataFrame) -> dict:
    """Top 10 / positions 11-50 / Top 50 views of a table that has a 'position' column."""
    return {"Top 10": df[df["position"] <= 10], "11-50": df[df["position"] > 10], "Top 50": df}


def collab_by_rank_group(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, part in split_by_band(clean).items():
        rows.append({"group": name, "entries": len(part),
                     "collab_share_%": collaboration_ratio(part) * 100 if len(part) else np.nan,
                     "avg_artists_per_song": avg_collaborators(part) if len(part) else np.nan})
    return pd.DataFrame(rows)


def collab_edges(clean: pd.DataFrame, min_weight: int = 1) -> pd.DataFrame:
    """Pairs of artists on the same song. weight = chart entries together."""
    rows = []
    for names, n in clean[clean["n_artists"] > 1].groupby("artist_list").size().items():
        a = names.split(" | ")
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                rows.append((a[i], a[j], n))
    if not rows:
        return pd.DataFrame(columns=["a", "b", "weight"])
    e = pd.DataFrame(rows, columns=["a", "b", "weight"])
    e = e.groupby(["a", "b"], as_index=False)["weight"].sum()
    return e[e["weight"] >= min_weight].sort_values("weight", ascending=False).reset_index(drop=True)


def network_stats(edges: pd.DataFrame, top: int = 10) -> dict:
    """Degree / weighted degree / components of the collaboration network (NetworkX)."""
    import networkx as nx
    G = nx.Graph()
    for _, r in edges.iterrows():
        G.add_edge(r["a"], r["b"], weight=int(r["weight"]))
    if G.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "components": 0, "density": np.nan, "top_degree": pd.DataFrame()}
    deg = pd.DataFrame({
        "artist": list(G.nodes()),
        "partners": [G.degree(n) for n in G.nodes()],
        "weighted_degree": [G.degree(n, weight="weight") for n in G.nodes()],
    }).sort_values(["partners", "weighted_degree"], ascending=False)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    return {
        "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "components": len(comps),
        "largest_component": len(comps[0]), "density": nx.density(G),
        "top_degree": deg.head(top).reset_index(drop=True),
    }


# ----------------------------------------------------------------- explicit
def explicit_share(clean: pd.DataFrame) -> float:
    return float(clean["is_explicit"].mean()) if len(clean) else np.nan


def explicit_by_rank_group(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, part in split_by_band(clean).items():
        rows.append({"rank_group": name, "entries": len(part),
                     "explicit_entries": int(part["is_explicit"].sum()),
                     "explicit_share_%": round(explicit_share(part) * 100, 1) if len(part) else np.nan})
    return pd.DataFrame(rows)


def explicit_by_position(clean: pd.DataFrame) -> pd.DataFrame:
    return (clean.groupby("position")["is_explicit"].mean() * 100).rename("explicit_share_%").reset_index()


def explicit_monthly(clean: pd.DataFrame) -> pd.DataFrame:
    mth = clean.assign(month=clean["date"].dt.to_period("M").dt.to_timestamp())
    return (mth.groupby("month")["is_explicit"].mean() * 100).rename("explicit_share_%").reset_index()


def explicit_vs_clean_popularity(clean: pd.DataFrame) -> pd.DataFrame:
    """Average popularity AND chart position of explicit vs clean entries."""
    g = clean.assign(content=clean["is_explicit"].map({True: "Explicit", False: "Clean"})).groupby("content")
    return pd.DataFrame({
        "entries": g.size(),
        "avg_popularity": g["popularity"].mean().round(2),
        "median_popularity": g["popularity"].median(),
        "avg_position": g["position"].mean().round(2),
        "top10_share_%": (g["position"].apply(lambda s: (s <= 10).mean()) * 100).round(1),
    }).reset_index()


# ----------------------------------------------------------------- album structure
def single_vs_album_ratio(clean: pd.DataFrame) -> float:
    """Singles : albums. Compilations (0.3% of entries) are excluded from the ratio."""
    s = (clean["album_type"] == "single").sum()
    a = (clean["album_type"] == "album").sum()
    return float(s / a) if a else np.nan


def single_share(clean: pd.DataFrame) -> float:
    """Singles / ALL entries (compilations included in the denominator)."""
    return float((clean["album_type"] == "single").mean()) if len(clean) else np.nan


def album_type_share(clean: pd.DataFrame) -> pd.DataFrame:
    c = clean["album_type"].value_counts()
    return pd.DataFrame({"album_type": c.index, "entries": c.values,
                         "share_%": (c.values / c.sum() * 100).round(1)})


def album_type_by_rank(clean: pd.DataFrame) -> pd.DataFrame:
    """Entries and % by rank group (Top 10 / 11-25 / 26-50) and album type."""
    t = clean.groupby(["rank_group", "album_type"], observed=True).size().reset_index(name="entries")
    t["share_in_group_%"] = (t["entries"] / t.groupby("rank_group", observed=True)["entries"].transform("sum") * 100).round(1)
    return t


def album_size_summary(clean: pd.DataFrame) -> pd.DataFrame:
    return clean.groupby("album_size_bucket", observed=True).agg(
        entries=("song", "size"), avg_position=("position", "mean"),
        avg_popularity=("popularity", "mean"),
    ).round(1).reset_index()


def album_size_stats(clean: pd.DataFrame) -> dict:
    """Large-release (12+ tracks) presence and size comparison for album-type entries."""
    alb = clean[clean["album_type"] == "album"]
    sg = clean[clean["album_type"] == "single"]
    return {
        "share_entries_12plus_tracks_%": round((clean["total_tracks"] >= 12).mean() * 100, 1),
        "share_album_entries_12plus_%": round((alb["total_tracks"] >= 12).mean() * 100, 1) if len(alb) else np.nan,
        "mean_tracks_album_entries": round(alb["total_tracks"].mean(), 1) if len(alb) else np.nan,
        "median_tracks_album_entries": float(alb["total_tracks"].median()) if len(alb) else np.nan,
        "avg_position_12plus": round(clean.loc[clean["total_tracks"] >= 12, "position"].mean(), 2),
        "avg_position_under12": round(clean.loc[clean["total_tracks"] < 12, "position"].mean(), 2),
        "single_entries": int(len(sg)),
    }


def album_flood_days(clean: pd.DataFrame, min_tracks: int = 3) -> pd.DataFrame:
    """Days where >= min_tracks songs from the same artist's same-size album are in the Top 50.
    (No album id in the data, so an album is approximated by lead artist + total_tracks.)"""
    alb = clean[clean["album_type"] == "album"]
    g = alb.groupby(["date", "lead_artist", "total_tracks"]).agg(
        tracks_in_chart=("song", "nunique"), best_position=("position", "min")).reset_index()
    return g[g["tracks_in_chart"] >= min_tracks].sort_values(["tracks_in_chart", "date"], ascending=[False, True])


def album_flood_summary(clean: pd.DataFrame, min_tracks: int = 3) -> pd.DataFrame:
    f = album_flood_days(clean, min_tracks)
    if f.empty:
        return pd.DataFrame(columns=["lead_artist", "flood_days", "max_tracks_in_chart"])
    return (f.groupby("lead_artist").agg(flood_days=("date", "nunique"),
                                         max_tracks_in_chart=("tracks_in_chart", "max"))
            .sort_values("flood_days", ascending=False).reset_index())


# ----------------------------------------------------------------- duration
def duration_summary(clean: pd.DataFrame) -> pd.DataFrame:
    return clean.groupby("duration_bucket", observed=True).agg(
        entries=("song", "size"), avg_popularity=("popularity", "mean"),
        avg_position=("position", "mean"),
    ).round(1).reset_index()


def duration_by_popularity_quartile(clean: pd.DataFrame) -> pd.DataFrame:
    return clean.groupby("popularity_quartile", observed=True).agg(
        entries=("song", "size"), min_popularity=("popularity", "min"), max_popularity=("popularity", "max"),
        avg_duration_min=("duration_min", "mean"), median_duration_min=("duration_min", "median"),
        avg_position=("position", "mean"),
    ).round(2).reset_index()


def duration_correlations(clean: pd.DataFrame) -> dict:
    d = clean.dropna(subset=["popularity"])
    rho_pop, p_pop = stats.spearmanr(d["duration_min"], d["popularity"])
    rho_pos, p_pos = stats.spearmanr(clean["duration_min"], clean["position"])
    return {"rho_duration_popularity": float(rho_pop), "p_duration_popularity": float(p_pop),
            "rho_duration_position": float(rho_pos), "p_duration_position": float(p_pos)}


def duration_by_rank_group(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, part in split_by_band(clean).items():
        rows.append({"group": name, "avg_duration_min": part["duration_min"].mean(),
                     "median_duration_min": part["duration_min"].median(),
                     "short_share_%": (part["duration_s"] < 180).mean() * 100})
    return pd.DataFrame(rows).round(2)


# ----------------------------------------------------------------- content variety
def _norm_entropy(series: pd.Series) -> float:
    p = series.value_counts(normalize=True)
    if len(p) <= 1:
        return 0.0
    return float(-(p * np.log(p)).sum() / np.log(len(p)))


def content_variety_parts(clean: pd.DataFrame, exploded: pd.DataFrame) -> dict:
    """Four 0..1 balance scores (normalised Shannon entropy; 1 = perfectly balanced)."""
    return {
        "artist mix": _norm_entropy(exploded["artist_name"]),
        "album type mix": _norm_entropy(clean["album_type"]),
        "explicit mix": _norm_entropy(clean["is_explicit"]),
        "duration mix": _norm_entropy(clean["duration_bucket"].astype(str)),
    }


def content_variety_index(clean: pd.DataFrame, exploded: pd.DataFrame) -> float:
    """Average of the four balance scores. > 0.75 = balanced, < 0.5 = skewed."""
    if clean.empty:
        return np.nan
    return float(np.mean(list(content_variety_parts(clean, exploded).values())))


# ----------------------------------------------------------------- domestic vs international
def country_share(exploded: pd.DataFrame, country_table: pd.DataFrame) -> pd.DataFrame:
    m = exploded.merge(country_table, left_on="artist_name", right_on="artist", how="left")
    m["country_group"] = m["country_group"].fillna("Unknown")
    c = m["country_group"].value_counts()
    return pd.DataFrame({"country_group": c.index, "appearances": c.values,
                         "share_%": (c.values / c.sum() * 100).round(1)})


def country_share_by_band(exploded: pd.DataFrame, country_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, part in split_by_band(exploded).items():
        cs = country_share(part, country_table).assign(group=name)
        rows.append(cs)
    return pd.concat(rows, ignore_index=True)


# ----------------------------------------------------------------- KPIs
def headline_kpis(clean: pd.DataFrame, exploded: pd.DataFrame) -> dict:
    """The seven KPIs required by the plan, plus the supporting diversity metrics."""
    return {
        "Artist Concentration Index": concentration_index(exploded),
        "Unique Artist Count": unique_artist_count(exploded),
        "Collaboration Ratio": collaboration_ratio(clean),
        "Explicit Content Share": explicit_share(clean),
        "Single vs Album Ratio": single_vs_album_ratio(clean),
        "Content Variety Index": content_variety_index(clean, exploded),
        "Top-5 Artist Share": top_n_share(exploded, 5),
        "Normalised Concentration": normalised_concentration(exploded),
        "Avg Daily Unique Artists": float(daily_unique_artists(exploded).mean()),
        "Daily Diversity Ratio": float(daily_diversity(exploded).mean()),
    }


def _day_kpis(c: pd.DataFrame, e: pd.DataFrame) -> dict:
    return {
        "artist_concentration": concentration_index(e),
        "unique_artists": unique_artist_count(e),
        "collaboration_ratio": collaboration_ratio(c),
        "explicit_share": explicit_share(c),
        "single_share": single_share(c),
        "single_vs_album_ratio": single_vs_album_ratio(c),
        "content_variety": content_variety_index(c, e),
        "top5_share": top_n_share(e, 5),
        "avg_duration_min": float(c["duration_min"].mean()),
    }


def daily_kpis(clean: pd.DataFrame, exploded: pd.DataFrame) -> pd.DataFrame:
    """Every KPI for every snapshot date."""
    ex_by_date = dict(tuple(exploded.groupby("date")))
    rows = []
    for d, c in clean.groupby("date"):
        rows.append({"date": d, **_day_kpis(c, ex_by_date[d])})
    return pd.DataFrame(rows)


def monthly_kpis(clean: pd.DataFrame, exploded: pd.DataFrame) -> pd.DataFrame:
    """KPIs computed over each calendar month (more stable than one 50-song day)."""
    cm = clean.assign(month=clean["date"].dt.to_period("M").dt.to_timestamp())
    em = exploded.assign(month=exploded["date"].dt.to_period("M").dt.to_timestamp())
    ex_by = dict(tuple(em.groupby("month")))
    rows = [{"month": mth, **_day_kpis(c, ex_by[mth])} for mth, c in cm.groupby("month")]
    return pd.DataFrame(rows)


def kpis_by_band(clean: pd.DataFrame, exploded: pd.DataFrame) -> pd.DataFrame:
    """Top 10 vs positions 11-50 vs Top 50, same KPI definitions in each column."""
    cs, es = split_by_band(clean), split_by_band(exploded)
    rows = {}
    for name in ["Top 10", "11-50", "Top 50"]:
        c, e = cs[name], es[name]
        rows[name] = {
            "Entries": len(c),
            "Unique Artist Count": unique_artist_count(e),
            "Artist Concentration Index": concentration_index(e),
            "Top-5 Artist Share": top_n_share(e, 5),
            "Collaboration Ratio": collaboration_ratio(c),
            "Avg Artists per Song": avg_collaborators(c),
            "Explicit Content Share": explicit_share(c),
            "Single Share of Entries": single_share(c),
            "Single vs Album Ratio": single_vs_album_ratio(c),
            "Avg Duration (min)": float(c["duration_min"].mean()),
            "Avg Popularity": float(pd.to_numeric(c["popularity"], errors="coerce").mean()),
            "Content Variety Index": content_variety_index(c, e),
        }
    return pd.DataFrame(rows)


def band_tests(clean: pd.DataFrame) -> pd.DataFrame:
    """Statistical tests Top 10 vs 11-50 (chi-square for shares, Mann-Whitney for numbers)."""
    t10, rest = clean[clean["position"] <= 10], clean[clean["position"] > 10]
    out = []

    def chi(label, col):
        tab = pd.crosstab(clean["position"] <= 10, col)
        chi2, p, _, _ = stats.chi2_contingency(tab)
        out.append({"comparison": label, "test": "chi-square", "statistic": chi2, "p_value": p})

    chi("Collaboration share", clean["is_collab"])
    chi("Explicit share", clean["is_explicit"])
    chi("Single vs non-single", clean["album_type"] == "single")
    for label, col in [("Duration (min)", "duration_min"), ("Popularity", "popularity"),
                       ("Artists per song", "n_artists")]:
        a, b = t10[col].dropna(), rest[col].dropna()
        u = stats.mannwhitneyu(a, b)
        out.append({"comparison": label, "test": "Mann-Whitney U", "statistic": u.statistic, "p_value": u.pvalue})
    return pd.DataFrame(out)


def component_layout(G, seed: int = 7) -> dict:
    """Lay out each connected cluster on its own and tile the clusters in a grid,
    so small clusters do not collapse on top of each other."""
    import math
    import networkx as nx
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    cols = max(1, math.ceil(math.sqrt(len(comps))))
    pos = {}
    for i, comp in enumerate(comps):
        sub = G.subgraph(comp)
        if len(comp) == 1:
            p = {next(iter(comp)): (0.0, 0.0)}
        elif len(comp) == 2:
            a, b = list(comp)
            p = {a: (-0.4, 0.0), b: (0.4, 0.0)}
        else:
            p = nx.spring_layout(sub, seed=seed, k=1.2 / math.sqrt(len(comp)), iterations=200)
        scale = 0.9 if len(comp) > 3 else 0.7
        cx, cy = (i % cols) * 2.6, -(i // cols) * 2.6
        for n, (x, y) in p.items():
            pos[n] = (cx + x * scale, cy + y * scale)
    return pos
