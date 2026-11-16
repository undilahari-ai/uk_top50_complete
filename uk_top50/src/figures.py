"""Step 4 - Static charts for the research paper (saved to reports/figures/).

Run:  python src/figures.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402
import metrics as m  # noqa: E402

OUT = ROOT / "reports" / "figures"
BLUE, GREY, ORANGE, TEAL = "#1F5FBF", "#9AA5B1", "#D9622B", "#1B8A78"
INK = "#222B36"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10, "axes.edgecolor": "#BBBBBB",
    "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
    "axes.titlesize": 11, "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "grid.color": "#E6E9ED", "grid.linewidth": 0.7, "axes.axisbelow": True,
})


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def labels(ax, bars, fmt="{:.1f}%", dy=0.5):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, fmt.format(b.get_height()),
                ha="center", va="bottom", fontsize=9)


def main():
    c = data.load_clean()
    e = data.explode_artists(c)
    countries = data.load_countries()

    # 1. leaderboard ------------------------------------------------------
    board = m.appearance_counts(e).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(board["artist_name"], board["appearances"], color=BLUE)
    for y, v, s in zip(range(len(board)), board["appearances"], board["share_%"]):
        ax.text(v + 15, y, f"{v:,}  ({s:.1f}%)", va="center", fontsize=8)
    ax.set_xlabel("Chart appearances (artist slots, days x songs)")
    ax.set_title("Fig 1. Artist dominance: 15 most frequent artists")
    ax.set_xlim(0, board["appearances"].max() * 1.22)
    ax.grid(axis="y", visible=False)
    save(fig, "fig01_top_artists.png")

    # 2. concentration / diversity over time -----------------------------
    mk = m.monthly_kpis(c, e)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    axs[0].plot(mk["month"], mk["unique_artists"], marker="o", color=BLUE)
    axs[0].set_title("Unique artists per month")
    axs[0].set_ylabel("Artists")
    axs[1].plot(mk["month"], mk["artist_concentration"], marker="o", color=ORANGE)
    axs[1].set_title("Artist Concentration Index per month")
    axs[1].set_ylabel("HHI (0-1)")
    for ax in axs:
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Fig 2. Diversity and concentration by month", fontweight="bold", y=1.02)
    save(fig, "fig02_diversity_over_time.png")

    # 3. Top 10 vs 11-50 -------------------------------------------------
    b = m.kpis_by_band(c, e)
    rows = ["Collaboration Ratio", "Explicit Content Share", "Single Share of Entries", "Top-5 Artist Share"]
    labs = ["Collaborations", "Explicit", "Singles", "Top-5 artist\nshare"]
    x = np.arange(len(rows))
    w = 0.27
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for i, (name, col) in enumerate([("Top 10", BLUE), ("11-50", GREY), ("Top 50", TEAL)]):
        vals = [b.loc[r, name] * 100 for r in rows]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=name, color=col)
        labels(ax, bars, "{:.0f}%", 0.6)
    ax.set_xticks(x, labs)
    ax.set_ylabel("Share (%)")
    ax.set_title("Fig 3. Top 10 vs positions 11-50 vs Top 50")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    save(fig, "fig03_top10_vs_top50.png")

    # 4. collaboration network ------------------------------------------
    edges = m.collab_edges(c)
    G = nx.Graph()
    for _, r in edges.iterrows():
        G.add_edge(r["a"], r["b"], weight=r["weight"])
    strength = dict(G.degree(weight="weight"))
    keep = sorted(strength, key=strength.get, reverse=True)[:45]
    H = G.subgraph(keep).copy()
    H.remove_nodes_from([n for n in list(H) if H.degree(n) == 0])
    pos = m.component_layout(H)
    deg = dict(H.degree())
    size = e["artist_name"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 6.5))
    nx.draw_networkx_edges(H, pos, ax=ax, edge_color="#C5CCD4",
                           width=[0.4 + np.log1p(d["weight"]) * 0.35 for *_, d in H.edges(data=True)])
    nx.draw_networkx_nodes(H, pos, ax=ax, node_size=[40 + size.get(n, 1) ** 0.75 for n in H],
                           node_color=[deg[n] for n in H], cmap="viridis", edgecolors="white", linewidths=0.6)
    nx.draw_networkx_labels(H, pos, ax=ax, labels={n: n for n in H if deg[n] >= 2}, font_size=6.5)
    ax.set_title("Fig 4. Collaboration network (45 most connected artists; colour = number of partners)")
    ax.axis("off")
    save(fig, "fig04_collab_network.png")

    # 5. explicit --------------------------------------------------------
    eg = m.explicit_by_rank_group(c)
    ep = m.explicit_by_position(c)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
    bars = axs[0].bar(eg["rank_group"], eg["explicit_share_%"], color=[BLUE, GREY, TEAL])
    labels(axs[0], bars, "{:.1f}%")
    axs[0].set_title("Explicit share by rank group")
    axs[0].set_ylabel("% of entries explicit")
    axs[0].set_ylim(0, 50)
    axs[1].scatter(ep["position"], ep["explicit_share_%"], s=16, color=BLUE)
    z = np.polyfit(ep["position"], ep["explicit_share_%"], 1)
    axs[1].plot(ep["position"], np.polyval(z, ep["position"]), color=ORANGE)
    axs[1].set_title("Explicit share at each chart position")
    axs[1].set_xlabel("Chart position (1 = top)")
    fig.suptitle("Fig 5. Explicit content and chart position", fontweight="bold", y=1.03)
    save(fig, "fig05_explicit.png")

    # 6. album type + size ----------------------------------------------
    t = m.album_type_by_rank(c)
    piv = t.pivot(index="rank_group", columns="album_type", values="share_in_group_%").fillna(0)
    sz = m.album_size_summary(c)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
    bottom = np.zeros(len(piv))
    for col, colr in [("single", BLUE), ("album", GREY), ("compilation", ORANGE)]:
        if col in piv:
            axs[0].bar(piv.index.astype(str), piv[col], bottom=bottom, label=col, color=colr)
            for i, v in enumerate(piv[col]):
                if v > 6:
                    axs[0].text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
            bottom += piv[col].values
    axs[0].set_title("Release type by rank group")
    axs[0].set_ylabel("% of entries")
    axs[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    bars = axs[1].bar(sz["album_size_bucket"].astype(str), sz["avg_position"], color=BLUE)
    labels(axs[1], bars, "{:.1f}", 0.3)
    axs[1].set_title("Average chart position by release size")
    axs[1].set_xlabel("Tracks on the release")
    axs[1].set_ylabel("Avg position (lower = better)")
    fig.suptitle("Fig 6. Singles vs albums", fontweight="bold", y=1.03)
    save(fig, "fig06_album.png")

    # 7. duration ---------------------------------------------------------
    q = m.duration_by_popularity_quartile(c)
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    axs[0].hist(c["duration_s"] / 60, bins=45, color=BLUE)
    axs[0].axvline(3, color=ORANGE, ls="--")
    axs[0].axvline(4, color=ORANGE, ls="--")
    axs[0].set_title("Track length")
    axs[0].set_xlabel("Minutes (dashed: 3 and 4 min)")
    s = c.sample(4000, random_state=1).dropna(subset=["popularity"])
    axs[1].scatter(s["duration_min"], s["popularity"], s=5, alpha=0.3, color=BLUE)
    axs[1].set_title("Length vs popularity (4,000 sampled entries)")
    axs[1].set_xlabel("Minutes")
    axs[1].set_ylabel("Popularity")
    axs[1].set_xlim(1, 7)
    bars = axs[2].bar(["Q1\n(lowest)", "Q2", "Q3", "Q4\n(highest)"], q["avg_duration_min"], color=BLUE)
    labels(axs[2], bars, "{:.2f}", 0.02)
    axs[2].set_ylim(2.8, 3.6)
    axs[2].set_title("Average length by popularity quartile")
    axs[2].set_ylabel("Minutes")
    fig.suptitle("Fig 7. Track duration", fontweight="bold", y=1.03)
    save(fig, "fig07_duration.png")

    # 8. domestic vs international --------------------------------------
    cb = m.country_share_by_band(e, countries)
    piv = cb.pivot(index="group", columns="country_group", values="share_%").reindex(["Top 10", "11-50", "Top 50"]).fillna(0)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    left = np.zeros(len(piv))
    for col, colr in [("UK", BLUE), ("US", ORANGE), ("Other", TEAL), ("Unknown", "#C9CED6")]:
        if col in piv:
            ax.barh(piv.index, piv[col], left=left, color=colr, label=col)
            for i, v in enumerate(piv[col]):
                if v > 5:
                    ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9)
            left += piv[col].values
    ax.invert_yaxis()
    ax.set_xlabel("Share of artist slots (%)")
    ax.set_title("Fig 8. Domestic (UK) vs international artists")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.grid(axis="y", visible=False)
    save(fig, "fig08_country.png")

    # 9. KPI timeline ----------------------------------------------------
    d = m.daily_kpis(c, e).set_index("date")
    r = d.rolling(14, min_periods=7).mean()
    panels = [("artist_concentration", "Artist Concentration Index"), ("unique_artists", "Unique artists per day"),
              ("collaboration_ratio", "Collaboration Ratio"), ("explicit_share", "Explicit Content Share"),
              ("single_share", "Singles share of entries"), ("top5_share", "Top-5 Artist Share (daily)")]
    fig, axs = plt.subplots(2, 3, figsize=(11, 5.4), sharex=True)
    for ax, (col, ttl) in zip(axs.ravel(), panels):
        ax.plot(d.index, d[col], color="#C9CED6", lw=0.8)
        ax.plot(r.index, r[col], color=BLUE, lw=1.6)
        ax.set_title(ttl, fontsize=10)
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Fig 9. KPIs for every snapshot date (grey = daily, blue = 14-day average)", fontweight="bold", y=1.0)
    save(fig, "fig09_kpi_timeline.png")

    print("saved", len(list(OUT.glob("*.png"))), "figures to", OUT)


if __name__ == "__main__":
    main()
