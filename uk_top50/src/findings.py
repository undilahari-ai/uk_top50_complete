"""Step 3 - Key numbers and statistical tests for the paper.

Run:  python src/findings.py
Saves findings.txt (readable) and reports/results.json (used by figures.py and build_report.py).
"""
import json
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402
import metrics as m  # noqa: E402


def compute():
    c = data.load_clean()
    e = data.explode_artists(c)
    countries = data.load_countries()
    return c, e, countries


def main():
    c, e, countries = compute()
    lines, P = [], None
    lines_append = lines.append
    P = lines_append
    R = {}  # machine-readable results

    P("UK TOP 50 - KEY FINDINGS")
    P(f"Period: {c['date'].min().date()} to {c['date'].max().date()} | days: {c['date'].nunique()} | entries: {len(c):,}")
    P("")
    P("== Headline KPIs (whole period) ==")
    k = m.headline_kpis(c, e)
    for name, v in k.items():
        P(f"{name}: {v:.4f}" if isinstance(v, float) else f"{name}: {v}")
    R["kpis"] = {a: float(b) for a, b in k.items()}
    R["period"] = {"start": str(c["date"].min().date()), "end": str(c["date"].max().date()),
                   "days": int(c["date"].nunique()), "entries": int(len(c)),
                   "unique_songs": int(c.groupby(["song", "artist"]).ngroups)}

    P("")
    P("== Top 10 vs positions 11-50 vs Top 50 (same KPI definitions) ==")
    bands = m.kpis_by_band(c, e)
    P(bands.round(3).to_string())
    P("")
    P(m.band_tests(c).to_string(index=False))
    R["bands"] = json.loads(bands.to_json())
    R["band_tests"] = json.loads(m.band_tests(c).to_json(orient="records"))

    P("")
    P("== Artist dominance: top 10 by appearances ==")
    board = m.appearance_counts(e)
    P(board.head(10).to_string(index=False))
    R["top_artists"] = json.loads(board.head(10).to_json(orient="records"))
    R["artists_over_100_days"] = int((board["appearances"] >= 100).sum())
    R["artists_one_song_only"] = int((board["unique_songs"] == 1).sum())
    R["median_appearances"] = float(board["appearances"].median())
    top10_share = board.head(10)["appearances"].sum() / board["appearances"].sum()
    P(f"Top-10 artists' share of all artist slots: {top10_share:.1%}")
    R["top10_artist_share"] = float(top10_share)

    P("")
    P("== Diversity over time ==")
    du = m.daily_unique_artists(e)
    P(f"Avg unique artists per day: {du.mean():.1f} (min {du.min()}, max {du.max()})")
    wu = m.weekly_unique_artists(e)
    P(f"Avg unique artists per week: {wu.mean():.1f}")
    R["daily_unique"] = {"mean": float(du.mean()), "min": int(du.min()), "max": int(du.max()),
                         "weekly_mean": float(wu.mean())}
    mk = m.monthly_kpis(c, e)
    R["monthly_hhi_range"] = [float(mk["artist_concentration"].min()), float(mk["artist_concentration"].max())]
    R["monthly_hhi_peak_month"] = str(mk.loc[mk["artist_concentration"].idxmax(), "month"].date())
    R["monthly_hhi_low_month"] = str(mk.loc[mk["artist_concentration"].idxmin(), "month"].date())

    P("")
    P("== Domestic vs international (see artist_country.csv) ==")
    cs = m.country_share(e, countries)
    P(cs.to_string(index=False))
    R["country"] = json.loads(cs.to_json(orient="records"))
    cb = m.country_share_by_band(e, countries)
    R["country_by_band"] = json.loads(cb.to_json(orient="records"))
    known = cs[cs["country_group"] != "Unknown"]
    uk = float(cs.loc[cs["country_group"] == "UK", "share_%"].sum())
    R["uk_share_of_labelled_%"] = round(uk / known["share_%"].sum() * 100, 1)

    P("")
    P("== Collaboration ==")
    P(m.collab_by_rank_group(c).round(2).to_string(index=False))
    P(f"Avg artists per song: {m.avg_collaborators(c):.2f} | avg artists per collaboration: {m.avg_artists_per_collab(c):.2f}")
    P(m.team_size_distribution(c).to_string(index=False))
    solo, collab = c[~c["is_collab"]], c[c["is_collab"]]
    P(f"Avg position: solo {solo['position'].mean():.1f} | collab {collab['position'].mean():.1f}")
    pv = mannwhitneyu(solo["position"], collab["position"]).pvalue
    P(f"Mann-Whitney p-value (position, solo vs collab): {pv:.2e}")
    edges = m.collab_edges(c)
    ns = m.network_stats(edges)
    P(f"Network: {ns['nodes']} artists, {ns['edges']} links, {ns['components']} clusters, "
      f"largest cluster {ns['largest_component']} artists, density {ns['density']:.4f}")
    P(ns["top_degree"].to_string(index=False))
    P("Strongest pairs (chart entries together):")
    P(edges.head(8).to_string(index=False))
    R["collab"] = {
        "ratio": m.collaboration_ratio(c), "avg_artists_song": m.avg_collaborators(c),
        "avg_artists_collab": m.avg_artists_per_collab(c),
        "team_sizes": json.loads(m.team_size_distribution(c).to_json(orient="records")),
        "by_band": json.loads(m.collab_by_rank_group(c).to_json(orient="records")),
        "avg_pos_solo": float(solo["position"].mean()), "avg_pos_collab": float(collab["position"].mean()),
        "p_solo_vs_collab": float(pv),
        "network": {k2: (float(v) if isinstance(v, float) else v) for k2, v in ns.items() if k2 != "top_degree"},
        "top_degree": json.loads(ns["top_degree"].to_json(orient="records")),
        "top_pairs": json.loads(edges.head(8).to_json(orient="records")),
    }

    P("")
    P("== Explicit ==")
    P(m.explicit_by_rank_group(c).to_string(index=False))
    evc = m.explicit_vs_clean_popularity(c)
    P(evc.to_string(index=False))
    ex, cl = c[c["is_explicit"]], c[~c["is_explicit"]]
    p_pos = mannwhitneyu(ex["position"], cl["position"]).pvalue
    p_pop = mannwhitneyu(ex["popularity"].dropna(), cl["popularity"].dropna()).pvalue
    P(f"Mann-Whitney p-value (position): {p_pos:.2e} | (popularity): {p_pop:.2e}")
    R["explicit"] = {"by_band": json.loads(m.explicit_by_rank_group(c).to_json(orient="records")),
                     "vs_clean": json.loads(evc.to_json(orient="records")),
                     "p_position": float(p_pos), "p_popularity": float(p_pop)}

    P("")
    P("== Album type ==")
    P(m.album_type_share(c).to_string(index=False))
    P(m.album_type_by_rank(c).to_string(index=False))
    sg, al = c[c["album_type"] == "single"], c[c["album_type"] == "album"]
    P(f"Avg position: single {sg['position'].mean():.1f} | album {al['position'].mean():.1f}")
    p_sa = mannwhitneyu(sg["position"], al["position"]).pvalue
    P(f"Mann-Whitney p-value (position, single vs album): {p_sa:.2e}")
    P(f"Single : album ratio (compilations excluded) = {m.single_vs_album_ratio(c):.3f}; "
      f"singles are {m.single_share(c):.1%} of ALL entries; compilations = {(c['album_type'] == 'compilation').sum()} entries")
    ass = m.album_size_stats(c)
    P(f"Album size: {ass}")
    P(m.album_size_summary(c).to_string(index=False))
    fl = m.album_flood_summary(c)
    P("Album 'flood' days (3+ songs from one album in the chart):")
    P(fl.head(8).to_string(index=False))
    R["album"] = {"share": json.loads(m.album_type_share(c).to_json(orient="records")),
                  "by_rank": json.loads(m.album_type_by_rank(c).to_json(orient="records")),
                  "avg_pos_single": float(sg["position"].mean()), "avg_pos_album": float(al["position"].mean()),
                  "p_single_vs_album": float(p_sa), "size_stats": {a: float(b) for a, b in ass.items()},
                  "size_summary": json.loads(m.album_size_summary(c).to_json(orient="records")),
                  "flood": json.loads(fl.head(8).to_json(orient="records")),
                  "flood_days_total": int(m.album_flood_days(c)["date"].nunique()),
                  "compilations": int((c["album_type"] == "compilation").sum()),
                  "single_share_all": m.single_share(c)}

    P("")
    P("== Duration ==")
    P(f"Mean length: {c['duration_min'].mean():.2f} min | median: {c['duration_min'].median():.2f} min | "
      f"under 3 min: {(c['duration_s'] < 180).mean():.1%} | over 4 min: {(c['duration_min'] >= 4).mean():.1%}")
    P(m.duration_summary(c).to_string(index=False))
    P(m.duration_by_popularity_quartile(c).to_string(index=False))
    corr = m.duration_correlations(c)
    P(f"Spearman duration vs popularity: {corr['rho_duration_popularity']:.3f} (p={corr['p_duration_popularity']:.1e}); "
      f"duration vs position: {corr['rho_duration_position']:.3f} (p={corr['p_duration_position']:.1e})")
    P(m.duration_by_rank_group(c).to_string(index=False))
    yearly = c.groupby(c["date"].dt.year)["duration_min"].mean()
    R["duration"] = {"mean": float(c["duration_min"].mean()), "median": float(c["duration_min"].median()),
                     "short_share": float((c["duration_s"] < 180).mean()),
                     "long_share": float((c["duration_min"] >= 4).mean()),
                     "buckets": json.loads(m.duration_summary(c).to_json(orient="records")),
                     "by_quartile": json.loads(m.duration_by_popularity_quartile(c).to_json(orient="records")),
                     "corr": corr, "by_band": json.loads(m.duration_by_rank_group(c).to_json(orient="records")),
                     "by_year": {str(k2): float(v) for k2, v in yearly.items()}}

    stay = c.groupby(["song", "artist"]).size()
    P("")
    P(f"Songs seen: {len(stay)} | median days on chart: {stay.median():.0f} | longest: {stay.max()} days")
    R["stay"] = {"songs": int(len(stay)), "median": float(stay.median()), "max": int(stay.max())}

    out = "\n".join(lines)
    print(out)
    (ROOT / "findings.txt").write_text(out, encoding="utf-8")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "results.json").write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
