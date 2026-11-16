# UK Top 50 Playlist - Market Structure, Artist Diversity & Content Localization

Analysis of 554 daily UK Top 50 playlist snapshots (18 May 2024 - 27 Nov 2025, 27,700 chart entries):
cleaning, KPIs, Top 10 vs Top 50 comparison, an interactive Streamlit dashboard, a research paper and an executive summary.

## What is in this folder

| Path | What it is |
|---|---|
| `data/raw.csv` | Original file (never edited) |
| `data/clean.csv` | Cleaned data, one row per chart entry |
| `data/exploded.csv` | Same data, one row per entry per artist |
| `data/cleaning_report.json` | What the cleaning checked and changed |
| `artist_country.csv` | Artist to UK / US / Other lookup (edit to improve the domestic vs international view) |
| `src/cleaning.py` | Step 1: validate and clean |
| `src/data.py` | Shared loading helpers |
| `src/metrics.py` | Step 2: every KPI and analysis function |
| `src/findings.py` | Step 3: key numbers and tests -> `findings.txt`, `reports/results.json` |
| `src/figures.py` | Step 4: charts -> `reports/figures/*.png` |
| `src/build_report.py` | Step 5: builds the paper and the executive summary |
| `app.py` | Streamlit dashboard |
| `reports/Research_Paper.docx` / `.pdf` | Research paper (EDA, methods, findings, recommendations) |
| `reports/Executive_Summary.docx` / `.pdf` | One-page summary for stakeholders |
| `tests/test_pipeline.py` | 15 automated checks |
| `requirements.txt`, `.streamlit/config.toml`, `.python-version`, `Dockerfile`, `render.yaml` | Deployment files |

## How to run it (step by step)

1. Install Python 3.10 or newer (3.11 recommended).
2. Open a terminal in this folder.
3. (Recommended) create a clean environment:
   - Mac/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
   - Windows: `python -m venv .venv` then `.venv\Scripts\activate`
4. Install the packages: `pip install -r requirements.txt`
5. Clean the data: `python src/cleaning.py`
6. Get the numbers: `python src/findings.py`
7. Make the charts: `python src/figures.py`
8. Build the paper and summary: `python src/build_report.py`
9. Start the dashboard: `streamlit run app.py` (your browser opens at http://localhost:8501)
10. Check everything works: `python -m pytest -q` (should say `15 passed`)

The data and reports are already generated in this folder, so you can go straight to step 9.

## Deploy the dashboard online (free, Streamlit Community Cloud)

1. Create a free GitHub account and a new **public** repository.
2. Upload everything in this folder to it (keep the `data` folder and `artist_country.csv`).
3. Go to https://share.streamlit.io and sign in with GitHub.
4. Click **Create app** -> **Deploy a public app from GitHub**.
5. Choose your repository, branch `main`, and main file path `app.py`.
6. Under **Advanced settings** choose Python 3.11. Click **Deploy**.
7. After a minute or two you get a link like `https://your-name-uk-top50.streamlit.app`. Put this link in your submission.
8. Open the link and click through every tab and filter once to confirm it works.

Other options:
- **Docker:** `docker build -t uk-top50 .` then `docker run -p 8501:8501 uk-top50`, open http://localhost:8501
- **Render.com:** connect the GitHub repository; `render.yaml` already has the settings.

## What the cleaning does

1. Converts dates (`18-05-2024`) to real dates and checks numbers and the explicit flag.
2. Checks every date has exactly positions 1-50, each once. 1 March 2025 has 100 rows (two mixed snapshots) so it is removed.
3. Finds missing dates (14 Mar, 25 Mar, 11 Jul, 13 Aug 2025, plus the removed 1 Mar).
4. Treats popularity `0` as missing (136 rows).
5. Trims spaces and fixes case, accents and punctuation so one artist has one spelling (SZA / sza, Charli XCX / Charli xcx, Lily-Rose Depp).
6. Splits collaborations on `&` but protects names like "Chase & Status" and "Earth, Wind & Fire".
7. Adds guest artists written in titles: `(feat. X)`, `(with X)`, `featuring X`.
8. Adds helper columns: `n_artists`, `is_collab`, duration, `rank_group`, `rank_band` (Top 10 / 11-50), `popularity_quartile`, `album_size_bucket`.

## KPI definitions

| KPI | Meaning |
|---|---|
| Artist Concentration Index | Sum of squared artist shares (0-1, HHI style). Higher = a few artists dominate |
| Unique Artist Count | Number of different artists |
| Collaboration Ratio | Songs with 2+ artists / all songs |
| Explicit Content Share | Explicit entries / all entries |
| Single vs Album Ratio | Singles / albums (compilations excluded) |
| Content Variety Index | Average balance (normalised Shannon entropy) of artist, release type, explicit and duration mix |
| Top-5 Artist Share | Share of artist slots held by the 5 most frequent artists |
| Daily Diversity Ratio | Unique artists / artist slots on one day, averaged over days |

## Dashboard

Tabs: Overview (KPIs and KPIs over time), Top 10 vs Top 50, Artist dominance, Collaboration (network), Explicit vs clean, Album type, Track duration, Help.
Sidebar filters: date range, artist, solo / collaboration, album type, chart positions (Top 50 / Top 10 / 11-50).

## Limitations

- Playlist snapshots, not real stream counts. "Appearances" are chart-days, so long-running songs weigh more.
- One date removed and four missing.
- Country labels were added by hand (about 95% of artist slots) and should be reviewed.
- The files do not say who owns or may share the data. Confirm the data source and attribution before presenting externally.
- No US or other-market data, so UK-vs-US explicit or duration comparisons are not possible.
