"""Shared loading helpers used by findings, figures, report builder, tests and the app."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

RANK_ORDER = ["Top 10", "11-25", "26-50"]
BAND_ORDER = ["Top 10", "11-50"]
DUR_ORDER = ["Short (<3 min)", "Medium (3-4 min)", "Long (>4 min)"]
POP_ORDER = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
SIZE_ORDER = ["1 (single)", "2-5", "6-12", "13-20", "21+"]


def load_clean(path: Path = None) -> pd.DataFrame:
    """Read data/clean.csv and restore dates and ordered categories."""
    path = path or ROOT / "data" / "clean.csv"
    c = pd.read_csv(path, parse_dates=["date"])
    c["popularity"] = pd.to_numeric(c["popularity"], errors="coerce")
    c["rank_group"] = pd.Categorical(c["rank_group"], RANK_ORDER, ordered=True)
    c["rank_band"] = pd.Categorical(c["rank_band"], BAND_ORDER, ordered=True)
    c["duration_bucket"] = pd.Categorical(c["duration_bucket"], DUR_ORDER, ordered=True)
    c["popularity_quartile"] = pd.Categorical(c["popularity_quartile"], POP_ORDER, ordered=True)
    c["album_size_bucket"] = pd.Categorical(c["album_size_bucket"], SIZE_ORDER, ordered=True)
    c["is_explicit"] = c["is_explicit"].astype(bool)
    c["is_collab"] = c["is_collab"].astype(bool)
    return c


def explode_artists(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per chart entry per artist."""
    return clean.assign(artist_name=clean["artist_list"].str.split(" | ", regex=False)).explode("artist_name")


def load_countries(path: Path = None) -> pd.DataFrame:
    return pd.read_csv(path or ROOT / "artist_country.csv")
