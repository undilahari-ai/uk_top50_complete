"""Run:  python -m pytest -q   (from the project folder, after `python src/cleaning.py`)"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import cleaning  # noqa: E402
import data  # noqa: E402
import metrics as m  # noqa: E402


@pytest.fixture(scope="module")
def c():
    return data.load_clean()


@pytest.fixture(scope="module")
def e(c):
    return data.explode_artists(c)


# ---- cleaning ---------------------------------------------------------
def test_every_day_has_positions_1_to_50_once(c):
    for _, g in c.groupby("date"):
        assert sorted(g["position"]) == list(range(1, 51))


def test_bad_snapshot_removed(c):
    assert pd.Timestamp("2025-03-01") not in set(c["date"])
    assert len(c) == 27700 and c["date"].nunique() == 554


def test_no_nulls_in_key_fields(c):
    assert not c[["date", "position", "song", "artist", "artist_list", "is_explicit"]].isna().any().any()


def test_popularity_zero_is_missing(c):
    assert (c["popularity"] == 0).sum() == 0 and c["popularity"].isna().sum() == 136


def test_artist_names_standardised(e):
    keys = e["artist_name"].map(cleaning.name_key)
    spell = e.groupby(keys)["artist_name"].nunique()
    assert spell.max() == 1, spell[spell > 1]
    names = set(e["artist_name"])
    assert {"SZA", "Charli XCX"} <= names and not {"sza", "Charli xcx"} & names


def test_split_rules():
    assert cleaning.split_artists("Chase & Status & Hedex") == ["Chase & Status", "Hedex"]
    assert cleaning.split_artists("Earth, Wind & Fire") == ["Earth, Wind & Fire"]
    assert cleaning.title_guests("Guess featuring billie eilish") == ["billie eilish"]
    assert cleaning.title_guests("Santa Baby (with Henri René & His Orchestra)") == ["Henri René & His Orchestra"]
    assert cleaning.tidy("  Ed   Sheeran ") == "Ed Sheeran"


def test_collab_flag_matches_count(c):
    assert ((c["n_artists"] > 1) == c["is_collab"]).all()


# ---- metrics ----------------------------------------------------------
def test_hhi_toy():
    ex = pd.DataFrame({"artist_name": ["a"] * 5 + ["b"] * 5})
    assert m.concentration_index(ex) == pytest.approx(0.5)
    assert m.top_n_share(ex, 1) == pytest.approx(0.5)
    assert m.normalised_concentration(ex) == pytest.approx(0.0)


def test_kpis_in_range(c, e):
    k = m.headline_kpis(c, e)
    assert 0 < k["Artist Concentration Index"] < 1 and k["Unique Artist Count"] == e["artist_name"].nunique()
    assert 0 < k["Collaboration Ratio"] < 1 and 0 < k["Content Variety Index"] <= 1
    assert k["Top-5 Artist Share"] > k["Artist Concentration Index"]


def test_top10_vs_rest_partition(c, e):
    t = m.kpis_by_band(c, e)
    assert t.loc["Entries", "Top 10"] + t.loc["Entries", "11-50"] == t.loc["Entries", "Top 50"]
    top50 = t.loc["Explicit Content Share", "Top 50"]
    mix = (t.loc["Explicit Content Share", "Top 10"] * 5540 + t.loc["Explicit Content Share", "11-50"] * 22160) / 27700
    assert mix == pytest.approx(top50)


def test_daily_kpis_cover_every_date(c, e):
    d = m.daily_kpis(c, e)
    assert len(d) == c["date"].nunique() and d["artist_concentration"].between(0, 1).all()


def test_popularity_quartiles_equal_size(c):
    n = c.dropna(subset=["popularity"]).groupby("popularity_quartile", observed=True).size()
    assert n.max() - n.min() <= 1 and len(n) == 4


def test_network(c):
    ns = m.network_stats(m.collab_edges(c))
    assert ns["nodes"] > 100 and ns["top_degree"].iloc[0]["partners"] >= ns["top_degree"].iloc[-1]["partners"]


def test_ratio_excludes_compilations(c):
    s, a = (c["album_type"] == "single").sum(), (c["album_type"] == "album").sum()
    assert m.single_vs_album_ratio(c) == pytest.approx(s / a)


def test_app_runs_headless():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
    assert not at.exception and len(at.tabs) == 8 and len(at.metric) >= 8
    at.sidebar.radio[1].set_value("Top 10").run()
    assert not at.exception
