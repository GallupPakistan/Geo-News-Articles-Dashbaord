# Geo News — Opinion Articles Dashboard

A multi-page Streamlit dashboard for the `Final_Geo_News_.xlsx` dataset (83 opinion articles),
branded with the Geo News logo and an "Opinions" banner background.

## Structure

```
geo_dashboard/
├── Home.py              ← entry point, run this with `streamlit run Home.py`
├── common.py            ← shared data loading + branding/CSS helpers
├── pages/
│   ├── 1_Authors.py      ← author leaderboard + per-author drill-down
│   ├── 2_Topics.py       ← keyword frequency + auto topic clustering
│   └── 3_Articles.py     ← full filterable/searchable table + CSV export
├── assets/
│   ├── geo_logo.png      ← cropped, transparent-background Geo News logo
│   └── opinions_banner.png ← background banner
├── geo_news_data.csv     ← bundled dataset
└── requirements.txt
```

Streamlit auto-detects the `pages/` folder and builds the sidebar navigation —
you don't need to wire pages together yourself. The numeric prefixes (`1_`,
`2_`, `3_`) just control the order they appear in the sidebar.

## Run it locally

Works with **any Python 3.9+** (3.9 through 3.13 and newer) — `requirements.txt`
only sets minimum versions, so `pip` resolves whatever build is compatible
with your interpreter. Use a virtual environment so it doesn't depend on
what else is installed on your machine:

**macOS / Linux**
```bash
cd geo_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

**Windows (PowerShell)**
```powershell
cd geo_dashboard
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run Home.py
```

If you have multiple Python versions installed and want to pin which one,
replace `python3`/`py` above with the specific interpreter, e.g. `python3.11`
or `py -3.11`.

Opens at `http://localhost:8501`. Use the sidebar to move between **Home**,
**Authors**, **Topics**, and **Articles**.

Check your Python version any time with `python3 --version` (or `py --version`
on Windows) — you need 3.9 or newer.

## Branding
- The Geo News logo sits in the sidebar on every page (pulled from
  `assets/geo_logo.png` — cropped tight and background removed from your
  uploaded logo file).
- The "Opinions" banner image is set as a soft, whitened background behind
  the main content on every page (`common.inject_branding`), so charts and
  tables stay readable on top of it.
- To swap either image, just replace the files in `assets/` and keep the
  same filenames.

## Filters & data
- Filters (date range, author, search) live in the sidebar and apply across
  **all pages** — they're shared via `st.session_state`, not per-page.
- Upload a replacement `.xlsx`/`.csv` from the **Home** page's sidebar
  uploader; every other page will pick up the new data automatically.
  Expected columns: `Title, Author, Publish Date, Language, Source,
  Summary (100 Words), Article URL`.

## Notes
- `Author` blanks are labeled "Unattributed / Staff" rather than dropped.
- Topic clusters (TF-IDF + KMeans) are unsupervised and recomputed on the
  *currently filtered* set, so names shift as you filter — that's expected.
