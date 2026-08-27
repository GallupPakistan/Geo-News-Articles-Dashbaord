# Geo News — Opinions Analytics

A single-page Streamlit dashboard for the `Final_Geo_News_.xlsx` opinion-article
dataset, redesigned around **auto-classified categories** instead of raw
publishing volume. Structure and layout are inspired by the Gallup Pakistan
OP-ED News Dashboard (Power BI): a sidebar classification checklist + filters,
and five tabs across the top.

## Structure

```
Home.py       ← entry point, run this with `streamlit run Home.py` — contains all 5 tabs
common.py     ← data loading, the rule-based classifier, and every chart's data prep
assets/       ← Geo News logo
Final_Geo_News_.xlsx
requirements.txt
```

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run Home.py
```

Opens at `http://localhost:8501`.

## The 5 tabs

1. **Overview** — headline KPIs, overall category mix, top authors.
2. **Classification Trends** — monthly share (%) of each category, as a
   multi-line trend (pick how many categories to show).
3. **Content & Categories** — category breakdown for a chosen month, overall
   category distribution, and the top recurring **themes** (phrases) inside
   whichever category you select.
4. **Language Wise** — language split, a word cloud of article text, and
   category mix by language.
5. **Authors & Sources** — top authors, per-source article counts, and each
   author's top category + article count.

## How classification works

The source data has no category column, so `common.py` scores each article's
title + summary against a keyword list per category (`CATEGORY_KEYWORDS`) —
title matches count double. Highest score wins; anything with no keyword hits
falls into **Society & Culture**. It's a transparent, editable dictionary, not
a black-box model — tune the keyword lists in `common.py` as coverage grows.

"Themes" within a category (Content & Categories tab) are the most frequent
2-word phrases in that category's articles, falling back to single words if
there isn't enough repeated text yet.

## Filters & data
- Sidebar: classification checklist (all categories, toggle any off),
  Language / News Papers / Year (shown only when the data has more than one
  value — right now everything is English / Geo TV, so those render as plain
  labels instead of empty dropdowns), Author, and a text search.
- To swap in a new dataset, replace `Final_Geo_News_.xlsx` (same columns:
  `Title, Author, Publish Date, Language, Source, Summary (100 Words),
  Article URL`) — everything else recomputes automatically, including new
  categories, trends, and themes.

## Notes
- `Author` blanks are labeled "Unattributed / Staff".
- The classifier and theme extraction are unsupervised/keyword-based and
  recompute on the currently filtered set, so results shift slightly as you
  filter — that's expected.
