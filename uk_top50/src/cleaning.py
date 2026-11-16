"""Step 1 - Ingest, validate and clean the raw UK Top 50 data.

Run:  python src/cleaning.py

Outputs
    data/clean.csv            one row per chart entry (song on a day)
    data/exploded.csv         one row per chart entry per artist
    data/cleaning_report.json what was checked / changed (used by the paper)
"""
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw.csv"

# --------------------------------------------------------------------------
# Name rules
# --------------------------------------------------------------------------
# Names that contain "&" or "," but are ONE act - never split these.
PROTECTED = [
    "Earth, Wind & Fire",
    "Tyler, The Creator",
    "Baddiel, Skinner & Lightning Seeds",
    "Florence + The Machine",
    "Simon & Garfunkel",
    "Hall & Oates",
    "Mumford & Sons",
    "Years & Years",
    "Kool & The Gang",
    "Crosby, Stills, Nash & Young",
    "Bell Biv DeVoe",
    "Chase & Status",
    "Richy Mitch & The Coal Miners",
    "Brooks & Dunn",
    "Henri René & His Orchestra",
    "Mitchell Ayres & His Orchestra",
]

# Same act written in different ways -> one name. None = not an artist, drop it.
ALIASES = {
    "The Lightning Seeds": "Baddiel, Skinner & Lightning Seeds",
    "Lightning Seeds": "Baddiel, Skinner & Lightning Seeds",
    "sped up + slowed": None,
    "More Lana Del Rey": "Lana Del Rey",
}

# Preferred official spelling when several spellings differ only by case,
# accents, hyphens or punctuation.
PREFERRED = ["SZA", "Charli XCX", "Lily-Rose Depp", "bb trickz"]

EXPECTED_POSITIONS = set(range(1, 51))


def name_key(name: str) -> str:
    """Spelling-proof key: no accents, no case, no punctuation or spaces."""
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", n.casefold())


def tidy(text: str) -> str:
    """Trim and collapse whitespace; normalise unicode form and curly quotes."""
    s = unicodedata.normalize("NFC", str(text))
    s = s.replace("’", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# Splitting artists
# --------------------------------------------------------------------------
def _protect(s: str):
    tokens = {}
    for i, name in enumerate(PROTECTED):
        key = f"@@P{i}@@"
        if re.search(re.escape(name), s, flags=re.IGNORECASE):
            s = re.sub(re.escape(name), key, s, flags=re.IGNORECASE)
            tokens[key] = name
    return s, tokens


def _restore(p: str, tokens: dict) -> str:
    for key, name in tokens.items():
        p = p.replace(key, name)
    return p.strip()


def split_names(text: str, seps) -> list:
    """Split a credit string on the separators, protecting fixed band names."""
    s, tokens = _protect(tidy(text))
    out = []
    for p in re.split(seps, s):
        p = _restore(p, tokens)
        if not p:
            continue
        p = ALIASES.get(p, p)
        if p:
            out.append(p)
    return out


def split_artists(text: str) -> list:
    """'A & B & C' -> ['A', 'B', 'C'] without breaking protected names."""
    return split_names(text, r"\s*&\s*")


GUEST_PATTERNS = [
    # (feat. X & Y)  [ft. X]  (featuring X)  (with X)
    re.compile(r"[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+([^)\]]+)[\)\]]", re.I),
    # "Song featuring X" / "Song - feat. X" (credit written outside brackets)
    re.compile(r"(?:^|\s)(?:feat\.|ft\.|featuring)\s+([^()\[\]-]+?)\s*$", re.I),
    # "Song version with X"
    re.compile(r"version with\s+([^()\[\]-]+?)\s*$", re.I),
]


def title_guests(song: str) -> list:
    """Guest artists written in the song title."""
    guests = []
    for pat in GUEST_PATTERNS:
        for m in pat.finditer(tidy(song)):
            guests += split_names(m.group(1), r"\s*(?:,|&|\band\b)\s*")
    return guests


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------
def validate_snapshots(df: pd.DataFrame) -> dict:
    """Check each date has exactly the positions 1..50 once each."""
    problems = {}
    for d, g in df.groupby("date"):
        pos = g["position"].tolist()
        if len(pos) != 50 or set(pos) != EXPECTED_POSITIONS or len(set(pos)) != len(pos):
            problems[d] = len(pos)
    return problems


def build_canonical_map(token_lists) -> dict:
    """key -> official spelling (preferred list, else most frequent spelling)."""
    counts = Counter(t for lst in token_lists for t in lst)
    by_key = {}
    for name, n in counts.items():
        by_key.setdefault(name_key(name), Counter())[name] += n
    pref = {name_key(p): p for p in PREFERRED}
    return {k: pref.get(k, spellings.most_common(1)[0][0]) for k, spellings in by_key.items()}


def main():
    df = pd.read_csv(RAW)
    report = {"raw_rows": int(len(df))}

    # ---- 1. types -------------------------------------------------------
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    for col in ["position", "duration_ms", "total_tracks"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["is_explicit"] = df["is_explicit"].astype(str).str.upper().map({"TRUE": True, "FALSE": False})
    report["null_cells_raw"] = {k: int(v) for k, v in df.isna().sum().items() if v}

    # ---- 2. missing key fields -----------------------------------------
    key_missing = df[["date", "position", "song", "artist"]].isna().any(axis=1)
    report["rows_missing_key_fields_dropped"] = int(key_missing.sum())
    df = df[~key_missing].copy()

    # ---- 3. text standardisation ---------------------------------------
    df["song"] = df["song"].map(tidy)
    df["artist"] = df["artist"].map(tidy)
    df["album_type"] = df["album_type"].map(tidy).str.lower()

    # ---- 4. snapshots that are not exactly positions 1..50 -------------
    counts = df.groupby("date").size()
    bad_days = sorted(set(counts[counts != 50].index) | set(validate_snapshots(df)))
    report["bad_days_dropped"] = [d.strftime("%Y-%m-%d") for d in bad_days]
    report["bad_day_row_counts"] = {d.strftime("%Y-%m-%d"): int(counts.get(d, 0)) for d in bad_days}
    df = df[~df["date"].isin(bad_days)].copy()

    before = len(df)
    df = df.drop_duplicates(["date", "song", "artist"])
    report["duplicate_rows_removed"] = int(before - len(df))

    all_days = pd.date_range(df["date"].min(), df["date"].max())
    report["missing_dates"] = [d.strftime("%Y-%m-%d") for d in all_days.difference(pd.DatetimeIndex(df["date"].unique()))]

    # ---- 5. popularity 0 means "no score" ------------------------------
    report["popularity_zero_rows"] = int((df["popularity"] == 0).sum())
    df["popularity"] = df["popularity"].replace(0, np.nan)

    # ---- 6. artist lists (credit + title guests, one spelling per act) --
    def raw_tokens(row):
        names = split_artists(row["artist"])
        have = {name_key(n) for n in names}
        for g in title_guests(row["song"]):
            if g == g.lower():  # lower-case titles ("featuring the 1975") -> Title Case
                g = " ".join(w[:1].upper() + w[1:] for w in g.split())
            if name_key(g) not in have:
                names.append(g)
                have.add(name_key(g))
        return names

    df["artist_list"] = df.apply(raw_tokens, axis=1)
    canon = build_canonical_map(df["artist_list"])

    def canonicalise(names):
        out, seen = [], set()
        for n in names:
            c = canon[name_key(n)]
            if name_key(c) not in seen:
                seen.add(name_key(c))
                out.append(c)
        return out or ["Unknown"]

    spelling_variants = Counter()
    for lst in df["artist_list"]:
        for n in lst:
            spelling_variants[(name_key(n), n)] += 1
    merged = {}
    for (k, n), _ in spelling_variants.items():
        merged.setdefault(k, set()).add(n)
    report["artist_spellings_merged"] = {canon[k]: sorted(v) for k, v in merged.items() if len(v) > 1}

    df["artist_list"] = df["artist_list"].map(canonicalise)
    df["n_artists"] = df["artist_list"].map(len)
    df["is_collab"] = df["n_artists"] > 1
    df["lead_artist"] = df["artist_list"].map(lambda x: x[0])
    report["guest_artists_from_titles"] = int(
        sum(1 for _, r in df.drop_duplicates(["song", "artist"]).iterrows()
            if len(title_guests(r["song"])) > 0)
    )

    # ---- 7. helper columns ---------------------------------------------
    df["duration_s"] = df["duration_ms"] / 1000
    df["duration_min"] = df["duration_ms"] / 60000
    df["duration_bucket"] = pd.cut(
        df["duration_min"], [0, 3, 4, 100],
        labels=["Short (<3 min)", "Medium (3-4 min)", "Long (>4 min)"], right=False,
    )
    df["rank_group"] = pd.cut(df["position"], [0, 10, 25, 50], labels=["Top 10", "11-25", "26-50"])
    df["rank_band"] = np.where(df["position"] <= 10, "Top 10", "11-50")
    # equal-sized popularity quartiles (rank first so ties do not collapse the bins)
    pop_rank = df["popularity"].rank(method="first")
    df["popularity_quartile"] = pd.qcut(
        pop_rank, 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
    )
    df["album_size_bucket"] = pd.cut(
        df["total_tracks"], [0, 1, 5, 12, 20, 500],
        labels=["1 (single)", "2-5", "6-12", "13-20", "21+"],
    )
    df = df.sort_values(["date", "position"]).reset_index(drop=True)

    # ---- 8. final validation (fails loudly) ----------------------------
    assert not validate_snapshots(df), "a day is not exactly positions 1..50"
    assert not df[["song", "artist", "artist_list"]].isna().any().any()
    assert df["is_explicit"].notna().all(), "unreadable explicit flag"
    assert df["position"].between(1, 50).all()
    assert df["duration_ms"].gt(0).all()
    assert df["date"].dtype.kind == "M"

    report.update({
        "clean_rows": int(len(df)),
        "days": int(df["date"].nunique()),
        "date_range": [df["date"].min().strftime("%Y-%m-%d"), df["date"].max().strftime("%Y-%m-%d")],
        "every_day_has_positions_1_to_50_once": True,
        "compilation_rows": int((df["album_type"] == "compilation").sum()),
    })

    # ---- 9. save --------------------------------------------------------
    save = df.copy()
    save["artist_list"] = save["artist_list"].map(" | ".join)
    drop = [c for c in ["album_cover_url"] if c in save.columns]
    save.drop(columns=drop).to_csv(ROOT / "data" / "clean.csv", index=False)

    ex = df.explode("artist_list").rename(columns={"artist_list": "artist_name"})
    ex.drop(columns=drop).to_csv(ROOT / "data" / "exploded.csv", index=False)

    report["unique_artists"] = int(ex["artist_name"].nunique())
    report["collab_share"] = round(float(df["is_collab"].mean()), 4)
    (ROOT / "data" / "cleaning_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("CLEANING REPORT")
    for k, v in report.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
