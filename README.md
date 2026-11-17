# UK Top 50 – Market Structure & Content Localization Analysis

An interactive data analytics project that explores the UK Top 50 music chart to understand artist dominance, collaboration patterns, content characteristics, and music-market trends.

## Live Dashboard

**[Open the Live Streamlit Dashboard](https://uk-top50-playlist-insights.streamlit.app/)**

## Project Overview

This project analyzes UK Top 50 chart data to identify patterns in music-market structure and content localization. It focuses on understanding how artists perform across chart positions and time, how collaborations contribute to chart representation, and how track characteristics vary.

The project combines data cleaning, exploratory data analysis, statistical metrics, visualizations, and an interactive Streamlit dashboard.

## Key Objectives

- Analyze artist dominance and representation in the UK Top 50.
- Compare the Top 10 with the overall Top 50.
- Measure artist diversity and concentration.
- Examine solo artists and collaborative tracks.
- Compare explicit and clean content.
- Analyze album and single representation.
- Explore track-duration and popularity patterns.
- Present findings through interactive visualizations.

## Dashboard Features

The dashboard includes eight sections:

1. **Overview** – Key performance indicators and overall chart insights.
2. **Top 10 vs Top 50** – Comparison of leading tracks with the full chart.
3. **Artist Dominance** – Artist representation and concentration patterns.
4. **Collaboration** – Analysis of solo and collaborative tracks.
5. **Explicit vs Clean** – Comparison of content categories.
6. **Album Type** – Analysis of album and single representation.
7. **Track Duration** – Exploration of song-length patterns.
8. **Help & Definitions** – Explanations of metrics and analytical terms.

### Interactive Filters

Users can explore the data using:
- Date range
- Artist
- Solo or collaboration
- Album type
- Chart position

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Data analysis and processing |
| Pandas | Data cleaning and manipulation |
| NumPy | Numerical calculations |
| Matplotlib / Plotly | Data visualization |
| Streamlit | Interactive dashboard |
| Pytest | Automated testing |
| Git & GitHub | Version control and project hosting |

## Project Structure

```text
uk_top50/
│
├── app.py
├── src/
│   ├── cleaning.py
│   ├── metrics.py
│   ├── findings.py
│   ├── data.py
│   ├── figures.py
│   └── build_report.py
│
├── data/
├── reports/
│   └── figures/
│
├── tests/
│   └── test_pipeline.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/undilahari-ai/uk_top50_complete.git
```

### 2. Open the Project Folder

```bash
cd uk_top50_complete/uk_top50
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Dashboard

```bash
python -m streamlit run app.py
```

The dashboard will open in your browser.

## Run Tests

To execute the automated test suite:

```bash
python -m pytest -q
```

**Latest local test result:** 15 tests passed.

## Key Analytical Metrics

- **Unique Artist Count:** Number of distinct artists in the selected data.
- **Artist Concentration Index:** Measures how concentrated chart representation is among artists.
- **Artist Diversity:** Examines the variety of artists represented.
- **Collaboration Analysis:** Studies solo and multi-artist track representation.
- **Popularity Analysis:** Examines average popularity across selected groups.

## Reports and Documentation

The project includes research documentation and executive summary reports, along with generated analytical figures in the `reports/` directory.

## Project Purpose

This project demonstrates practical skills in Python programming, data analytics, data visualization, statistical analysis, dashboard development, and automated testing.

## Author

**Undi Lahari**  
BCA – Computer Applications  
B.V. Raju College, Bhimavaram

## License

This project is intended for educational and academic purposes.
